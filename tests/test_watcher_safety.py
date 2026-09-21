"""The restraint measures in examples/watch_favorites.py: identity, budget, blocks, locking."""

import base64
import fcntl
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin

import pytest
import responses

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

import watch_favorites as wf  # noqa: E402
from tgtg import API_ITEM_ENDPOINT, BASE_URL, DATADOME_SDK_URL, TgtgClient  # noqa: E402
from tgtg.exceptions import TgtgAPIError  # noqa: E402

CAPTCHA_403 = b'{"url":"https://geo.captcha-delivery.com/interstitial/?initialCid=abc&cid=def"}'
UNAUTHORIZED_403 = b'{"errors":[{"code":"UNAUTHORIZED"}]}'


def build_watcher(tmp_path, credentials_token="a", **overrides):
    credentials = tmp_path / "creds.json"
    wf.save_credentials(credentials, {"access_token": credentials_token, "refresh_token": "r", "cookie": "datadome=d"})
    state = tmp_path / "state.json"
    wf.save_state(state, {"user_agent": "TGTG/1 test", "correlation_id": "cid-1"})

    args = wf.build_parser().parse_args([])
    args.credentials = credentials
    args.state = state
    args.active_hours_window = None
    for key, value in overrides.items():
        setattr(args, key, value)
    return wf.Watcher(args, wf.Notifier())


def test_device_identity_survives_restart(tmp_path):
    """A new user agent and correlation id on every launch makes one device look like many."""
    watcher = build_watcher(tmp_path)
    assert watcher.client.user_agent == "TGTG/1 test"
    assert watcher.client.correlation_id == "cid-1"


def test_repeated_captcha_blocks_escalate_then_stop(tmp_path):
    watcher = build_watcher(tmp_path)
    exc = TgtgAPIError(403, CAPTCHA_403)

    delays = [watcher.handle_api_error(exc) for _ in range(wf.MAX_CONSECUTIVE_BLOCKS)]

    assert delays[:3] == [300, 600, 1200], "backoff must double on each consecutive block"
    assert delays[-1] is None, "the watcher must give up instead of retrying forever"


def test_auth_failure_is_not_counted_as_a_block(tmp_path):
    watcher = build_watcher(tmp_path)

    assert watcher.handle_api_error(TgtgAPIError(403, UNAUTHORIZED_403)) == wf.BLOCK_BACKOFF_BASE
    assert watcher.blocks == 0
    assert watcher.handle_api_error(TgtgAPIError(429, b"{}")) == wf.RATE_LIMIT_BACKOFF


def test_error_payloads_are_redacted_before_logging(tmp_path, capsys):
    watcher = build_watcher(tmp_path)
    secret = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.c2ln"

    watcher.handle_api_error(TgtgAPIError(500, f'{{"token":"{secret}"}}'.encode()))

    assert secret not in capsys.readouterr().out


def test_daily_poll_budget_caps_and_rolls_over(tmp_path):
    watcher = build_watcher(tmp_path, max_polls_per_day=3)
    watcher.state.update(day=datetime.now().strftime("%Y-%m-%d"), polls=3)
    assert watcher._budget_left() == 0

    watcher.state["day"] = "1999-01-01"
    assert watcher._budget_left() == 3, "counters must reset on a new day"


def test_reservation_cap_blocks_further_orders(tmp_path):
    watcher = build_watcher(tmp_path, max_reserves_per_day=0, reserve=1)
    item = {"item": {"item_id": "1"}, "display_name": "Shop", "items_available": 5}

    assert watcher.try_reserve(item) is False, "no order may be placed once the daily cap is hit"


@pytest.mark.parametrize(
    "value,expected",
    [("7-23", (7, 23)), ("0-24", None), ("22-6", (22, 6)), ("", None)],
)
def test_parse_active_hours(value, expected):
    assert wf.parse_active_hours(value) == expected


@pytest.mark.parametrize("value", ["7", "7-99", "abc-1"])
def test_parse_active_hours_rejects_nonsense(value):
    with pytest.raises(ValueError):
        wf.parse_active_hours(value)


def test_active_window_waits_until_it_opens():
    assert wf.seconds_until_active((7, 23), datetime(2026, 9, 21, 10, 0)) == 0
    assert wf.seconds_until_active((7, 23), datetime(2026, 9, 21, 3, 0)) == 4 * 3600
    assert wf.seconds_until_active(None, datetime(2026, 9, 21, 3, 0)) == 0


def test_active_window_handles_overnight_ranges():
    assert wf.seconds_until_active((22, 6), datetime(2026, 9, 21, 23, 0)) == 0
    assert wf.seconds_until_active((22, 6), datetime(2026, 9, 21, 2, 0)) == 0
    assert wf.seconds_until_active((22, 6), datetime(2026, 9, 21, 10, 0)) == 12 * 3600


def test_only_one_watcher_can_run_at_a_time(tmp_path):
    lock_path = tmp_path / "watcher.lock"
    first = wf.acquire_lock(lock_path)
    assert first is not None

    assert wf.acquire_lock(lock_path) is None, "a second watcher must refuse to start"

    fcntl.flock(first, fcntl.LOCK_UN)
    first.close()
    second = wf.acquire_lock(lock_path)
    assert second is not None, "the lock must be reusable once released"
    second.close()


def test_captcha_block_is_distinguished_from_auth_failure():
    assert wf.is_captcha_block(str(CAPTCHA_403))
    assert not wf.is_captcha_block(str(UNAUTHORIZED_403))


def test_list_favourites_shows_every_store(tmp_path, capsys):
    """--store filters need the names, and those are only discoverable from a full listing."""
    watcher = build_watcher(tmp_path)
    watcher.client.get_favorites = lambda: [
        {"item": {"item_id": "1"}, "display_name": "Bakery Central", "items_available": 2},
        {"item": {"item_id": "2"}, "display_name": "Sushi Place", "items_available": 0},
    ]

    watcher.list_favourites()

    out = capsys.readouterr().out
    assert "Bakery Central" in out and "Sushi Place" in out
    assert "AVAILABLE" in out
    assert watcher.state["polls"] == 1


def _raise_captcha(_self):
    raise TgtgAPIError(403, CAPTCHA_403)


def test_list_reports_a_block_without_a_traceback(tmp_path, monkeypatch, capsys):
    """One-shot commands must explain a block, not dump a stack trace at the user."""
    credentials = tmp_path / "creds.json"
    wf.save_credentials(credentials, {"access_token": "a", "refresh_token": "r", "cookie": "datadome=d"})
    state = tmp_path / "state.json"
    wf.save_state(state, {"user_agent": "TGTG/1 test", "correlation_id": "cid-1"})
    monkeypatch.setattr(wf.Watcher, "list_favourites", _raise_captcha)

    code = wf.main(["--list", "--credentials", str(credentials), "--state", str(state)])

    out = capsys.readouterr().out
    assert code == 2
    assert "captcha" in out.lower()
    assert "Traceback" not in out


def test_explain_api_error_covers_each_case():
    assert "captcha" in wf.explain_api_error(TgtgAPIError(403, CAPTCHA_403)).lower()
    assert "credentials" in wf.explain_api_error(TgtgAPIError(403, UNAUTHORIZED_403)).lower()
    assert "rate limited" in wf.explain_api_error(TgtgAPIError(429, b"{}")).lower()
    assert "eyJ" not in wf.explain_api_error(TgtgAPIError(500, b'{"t":"eyJhbGciOi.JhbGci.sig"}'))


def test_diagnose_reports_a_blocked_network(tmp_path):
    """The probe must name the network as the culprit when even a fresh client is challenged."""
    responses.add(responses.POST, DATADOME_SDK_URL, json={"status": 200, "cookie": "datadome=d"}, status=200)
    responses.add(responses.POST, urljoin(BASE_URL, API_ITEM_ENDPOINT), body=CAPTCHA_403, status=403)

    args = wf.build_parser().parse_args([])
    assert wf.diagnose(args) == 2


def test_diagnose_reports_a_clean_network(tmp_path, capsys):
    """An UNAUTHORIZED answer means DataDome let the request reach tgtg, so the network is fine."""
    responses.add(responses.POST, DATADOME_SDK_URL, json={"status": 200, "cookie": "datadome=d"}, status=200)
    responses.add(responses.POST, urljoin(BASE_URL, API_ITEM_ENDPOINT), body=UNAUTHORIZED_403, status=403)

    args = wf.build_parser().parse_args([])
    assert wf.diagnose(args) == 0
    assert "NETWORK OK" in capsys.readouterr().out


def test_reset_identity_forgets_the_fingerprint_but_keeps_tokens(tmp_path):
    credentials = tmp_path / "creds.json"
    wf.save_credentials(credentials, {"access_token": "a", "refresh_token": "r", "cookie": "s=1; Datadome=BURNED"})
    state = tmp_path / "state.json"
    wf.save_state(state, {"user_agent": "TGTG/1 test", "correlation_id": "cid-1", "polls": 7})

    args = wf.build_parser().parse_args([])
    args.credentials, args.state = credentials, state
    assert wf.reset_identity(args) == 0

    new_state = json.loads(state.read_text(encoding="utf-8"))
    new_credentials = json.loads(credentials.read_text(encoding="utf-8"))
    assert "user_agent" not in new_state and "correlation_id" not in new_state
    assert new_state["polls"] == 7, "unrelated counters must survive"
    assert "BURNED" not in new_credentials["cookie"]
    assert new_credentials["access_token"] == "a", "auth tokens must be kept"


def test_reset_identity_survives_a_datadome_only_cookie(tmp_path):
    """The real credential file held nothing but a datadome cookie; clearing it emptied the field."""
    credentials = tmp_path / "creds.json"
    wf.save_credentials(credentials, {"access_token": "a", "refresh_token": "r", "cookie": "datadome=BURNED; Path=/"})
    state = tmp_path / "state.json"
    wf.save_state(state, {"user_agent": "TGTG/1 test", "correlation_id": "cid-1"})

    args = wf.build_parser().parse_args([])
    args.credentials, args.state = credentials, state
    wf.reset_identity(args)

    reset = json.loads(credentials.read_text(encoding="utf-8"))
    assert reset["cookie"] == "", "a datadome-only cookie leaves nothing behind"
    # The client must still be constructible and able to log in from that state.
    client = TgtgClient(**reset, user_agent="ua")
    assert client._already_logged


def _jwt(exp_offset_seconds):
    claims = {"exp": int((datetime.now() + timedelta(seconds=exp_offset_seconds)).timestamp())}
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"header.{body}.signature"


def test_access_token_expiry_is_read_from_the_jwt():
    expiry = wf.access_token_expiry(_jwt(3600))
    assert expiry is not None
    assert 3500 < (expiry - datetime.now()).total_seconds() < 3700
    assert wf.access_token_expiry("not-a-jwt") is None
    assert wf.access_token_expiry(None) is None


def test_a_valid_token_skips_the_refresh_endpoint(tmp_path):
    """Refreshing hits the most protected endpoint, so a live token must not trigger one."""
    watcher = build_watcher(tmp_path, credentials_token=_jwt(40 * 3600))

    assert watcher.client.last_time_token_refreshed is not None
    assert watcher.client.access_token_lifetime > 39 * 3600
    assert watcher.client._refresh_token() is None, "a live token must not be refreshed"


def test_an_expiring_token_still_refreshes(tmp_path):
    watcher = build_watcher(tmp_path, credentials_token=_jwt(60))
    assert watcher.client.last_time_token_refreshed is None, "a token about to die must be refreshed"
