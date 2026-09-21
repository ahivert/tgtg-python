"""Security behaviour of the credential handling in examples/watch_favorites.py."""

import json
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

import watch_favorites as wf  # noqa: E402

FAKE = {"access_token": "eyJhbGc.fake.payload", "refresh_token": "r" * 60, "cookie": "datadome=x"}


def _mode(path):
    return stat.S_IMODE(path.stat().st_mode)


def test_saved_credentials_are_private(tmp_path):
    target = tmp_path / "creds.json"
    wf.save_credentials(target, FAKE)

    assert _mode(target) == 0o600
    assert json.loads(target.read_text(encoding="utf-8")) == FAKE
    assert not list(tmp_path.glob("*.tmp")), "temp file left behind"


def test_saving_replaces_atomically(tmp_path):
    target = tmp_path / "creds.json"
    wf.save_credentials(target, FAKE)
    wf.save_credentials(target, {**FAKE, "access_token": "second"})

    assert json.loads(target.read_text(encoding="utf-8"))["access_token"] == "second"
    assert _mode(target) == 0o600


def test_loose_permissions_are_tightened_on_load(tmp_path):
    target = tmp_path / "creds.json"
    target.write_text(json.dumps(FAKE), encoding="utf-8")
    target.chmod(0o644)

    assert wf.load_credentials(target) == FAKE
    assert _mode(target) == 0o600


REALISTIC_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.ZmFrZXNpZ25hdHVyZQ"


def test_redact_hides_tokens():
    message = f"boom {FAKE['access_token']} and {REALISTIC_JWT} and {'A' * 50} end"
    cleaned = wf.redact(message)

    assert FAKE["access_token"] not in cleaned
    assert REALISTIC_JWT not in cleaned
    assert "eyJ" not in cleaned
    assert "A" * 50 not in cleaned
    assert cleaned.startswith("boom ") and cleaned.endswith(" end")


def test_credentials_path_resolution(tmp_path, monkeypatch):
    explicit = tmp_path / "explicit.json"
    monkeypatch.setenv("TGTG_CREDENTIALS", str(tmp_path / "from_env.json"))
    assert wf.resolve_credentials_path(explicit) == explicit
    assert wf.resolve_credentials_path(None) == tmp_path / "from_env.json"

    monkeypatch.delenv("TGTG_CREDENTIALS")
    assert wf.resolve_credentials_path(None) == wf.DEFAULT_CREDENTIALS


def test_legacy_credentials_are_moved_out_of_the_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    legacy = tmp_path / wf.LEGACY_CREDENTIALS
    legacy.write_text(json.dumps(FAKE), encoding="utf-8")
    target = tmp_path / "config" / "credentials.json"

    wf.migrate_legacy_credentials(target)

    assert not legacy.exists(), "the secret must not stay in the repository"
    assert json.loads(target.read_text(encoding="utf-8")) == FAKE
    assert _mode(target) == 0o600
    assert _mode(target.parent) == 0o700
