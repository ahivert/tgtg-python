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


def test_refresh_token_after_some_time(login_response):
    # login the client for the first time
    client = TgtgClient(email="test@test.com", password="test")
    client._login()

    new_access_token = "new_access_token"
    new_refresh_token = "new_refresh_token"

    responses.add(
        responses.POST,
        urljoin(BASE_URL, REFRESH_ENDPOINT),
        json={"access_token": new_access_token, "refresh_token": new_refresh_token},
        status=200,
    )

    # token lifetime is ok, no need to refresh
    with freeze_time(
        datetime.datetime.now()
        + datetime.timedelta(seconds=DEFAULT_ACCESS_TOKEN_LIFETIME)
    ):
        client._login()
        assert client.access_token != new_access_token
        assert client.refresh_token != new_refresh_token

    # token lifetime expired, refresh needed
    with freeze_time(
        datetime.datetime.now()
        + datetime.timedelta(seconds=DEFAULT_ACCESS_TOKEN_LIFETIME + 1)
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
        + datetime.timedelta(seconds=DEFAULT_ACCESS_TOKEN_LIFETIME + 1)
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


def test_login_empty_user_id_fail():
    with pytest.raises(ValueError):
        TgtgClient(access_token="test_token")._login()


def test_login_with_missing_refresh_token():
    with pytest.raises(Exception):
        TgtgClient(
            email="test@test.com", password="test", token_file="non_existant_file"
        )._login()


@pytest.fixture(scope="session")
def image_file(tmpdir_factory):
    fn = tmpdir_factory.mktemp("data").join("state")
    open(fn, "w").write('{"user_id":1234,"refresh_token":"a_refresh_token"}')
    return fn


def test_login_with_refresh_token(image_file):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, REFRESH_ENDPOINT),
        json={
            "access_token": "an_access_token",
            "refresh_token": "a_refresh_token",
            "startup_data": {"user": {"user_id": 1234}},
        },
        status=200,
    )
    client = TgtgClient(email="test@test.com", password="test", token_file=image_file)

    assert client.access_token == "an_access_token"
    assert client.refresh_token == "a_refresh_token"
    assert client.user_id == 1234
