from urllib.parse import urljoin

import pytest
import responses

from tgtg import BASE_URL, LOGIN_ENDPOINT, TgtgClient
from tgtg.exceptions import TgtgLoginError


@pytest.fixture
def remove_auth_env_var(monkeypatch):
    monkeypatch.delenv("TGTG_EMAIL", raising=False)
    monkeypatch.delenv("TGTG_PASSWORD", raising=False)


@responses.activate
def test_login_with_email_password_success(remove_auth_env_var):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, LOGIN_ENDPOINT),
        json={
            "access_token": "an_access_token",
            "startup_data": {"user": {"user_id": 1234}},
        },
        status=200,
    )
    client = TgtgClient(email="test@test.com", password="test")
    client._login()
    assert client.access_token == "an_access_token"
    assert client.user_id == 1234


@responses.activate
def test_login_with_bad_email_or_password_fail(remove_auth_env_var):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, LOGIN_ENDPOINT),
        json={"errors": [{"code": "FAILED LOGIN"}]},
        status=403,
    )
    with pytest.raises(TgtgLoginError):
        TgtgClient(email="test@test.com", password="test")._login()


def test_login_with_token_user_id_success(remove_auth_env_var):
    client = TgtgClient(access_token="an_access_token", user_id=1234)
    client._login()
    assert client.access_token == "an_access_token"
    assert client.user_id == 1234


def test_login_empty_fail(remove_auth_env_var):
    with pytest.raises(ValueError):
        TgtgClient()._login()


def test_login_empty_email_fail(remove_auth_env_var):
    with pytest.raises(ValueError):
        TgtgClient(password="test")._login()


def test_login_empty_token_fail(remove_auth_env_var):
    with pytest.raises(ValueError):
        TgtgClient(user_id=1234)._login()
