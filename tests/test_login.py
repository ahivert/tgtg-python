import datetime
from urllib.parse import urljoin

import pytest
import responses
from freezegun import freeze_time

from tgtg import (
    BASE_URL,
    DEFAULT_ACCESS_TOKEN_LIFETIME,
    LOGIN_ENDPOINT,
    REFRESH_ENDPOINT,
    TgtgClient,
)
from tgtg.exceptions import TgtgAPIError, TgtgLoginError


def test_login_with_email_password_success():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, LOGIN_ENDPOINT),
        json={
            "access_token": "an_access_token",
            "refresh_token": "a_refresh_token",
            "startup_data": {"user": {"user_id": 1234}},
        },
        status=200,
    )
    client = TgtgClient(email="test@test.com", password="test")
    client._login()
    assert client.access_token == "an_access_token"
    assert client.user_id == 1234


def test_login_with_bad_email_or_password_fail():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, LOGIN_ENDPOINT),
        json={"errors": [{"code": "FAILED LOGIN"}]},
        status=403,
    )
    with pytest.raises(TgtgLoginError):
        TgtgClient(email="test@test.com", password="test")._login()


def test_login_with_token_user_id_success():
    client = TgtgClient(access_token="an_access_token", user_id=1234)
    client._login()
    assert client.access_token == "an_access_token"
    assert client.user_id == 1234


def test_refresh_token_after_some_time(login_response):
    new_access_token = "new_access_token"
    new_refresh_token = "new_refresh_token"
    responses.add(
        responses.POST,
        urljoin(BASE_URL, REFRESH_ENDPOINT),
        json={"access_token": new_access_token, "refresh_token": new_refresh_token},
        status=200,
    )
    client = TgtgClient(email="test@test.com", password="test")
    client._login()
    assert client.access_token != new_access_token
    assert client.refresh_token != new_refresh_token
    with freeze_time(
        datetime.datetime.now()
        + datetime.timedelta(seconds=DEFAULT_ACCESS_TOKEN_LIFETIME)
    ):
        client._login()
        assert client.access_token == new_access_token
        assert client.refresh_token == new_refresh_token


def test_refresh_token_fail(login_response):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, REFRESH_ENDPOINT),
        json={},
        status=400,
    )
    client = TgtgClient(email="test@test.com", password="test")
    client._login()
    old_access_token = client.access_token
    old_refresh_token = client.refresh_token
    with freeze_time(
        datetime.datetime.now()
        + datetime.timedelta(seconds=DEFAULT_ACCESS_TOKEN_LIFETIME)
    ):
        with pytest.raises(TgtgAPIError):
            client._login()
        assert old_access_token == client.access_token
        assert old_refresh_token == client.refresh_token


def test_login_empty_fail():
    with pytest.raises(ValueError):
        TgtgClient()._login()


def test_login_empty_email_fail():
    with pytest.raises(ValueError):
        TgtgClient(password="test")._login()


def test_login_empty_token_fail():
    with pytest.raises(ValueError):
        TgtgClient(user_id=1234)._login()
