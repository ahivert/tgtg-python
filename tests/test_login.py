import datetime
from urllib.parse import urljoin

import pytest
import responses
from freezegun import freeze_time

from tgtg import BASE_URL, DEFAULT_ACCESS_TOKEN_LIFETIME, REFRESH_ENDPOINT, TgtgClient
from tgtg.exceptions import TgtgAPIError

from .constants import tgtg_client_fake_tokens


def test_refresh_token_after_some_time(refresh_tokens_response):
    # login the client for the first time
    client = TgtgClient(**tgtg_client_fake_tokens)
    new_access_token = "new_access_token"
    new_refresh_token = "new_refresh_token"

    responses.replace(
        responses.POST,
        urljoin(BASE_URL, REFRESH_ENDPOINT),
        json={"access_token": new_access_token, "refresh_token": new_refresh_token},
        status=200,
        headers={"set-cookie": "sweet sweet cookie"},
    )

    # token lifetime is ok, no need to refresh
    with freeze_time(
        datetime.datetime.now()
        + datetime.timedelta(seconds=DEFAULT_ACCESS_TOKEN_LIFETIME)
    ):
        client._refresh_token()
        assert client.access_token != new_access_token
        assert client.refresh_token != new_refresh_token

    # token lifetime expired, refresh needed
    with freeze_time(
        datetime.datetime.now()
        + datetime.timedelta(seconds=DEFAULT_ACCESS_TOKEN_LIFETIME + 1)
    ):
        client._refresh_token()
        assert client.access_token == new_access_token
        assert client.refresh_token == new_refresh_token


def test_refresh_token_fail(refresh_tokens_response):
    client = TgtgClient(**tgtg_client_fake_tokens)
    old_access_token = client.access_token
    old_refresh_token = client.refresh_token

    responses.replace(
        responses.POST,
        urljoin(BASE_URL, REFRESH_ENDPOINT),
        json={},
        status=400,
    )
    with freeze_time(
        datetime.datetime.now()
        + datetime.timedelta(seconds=DEFAULT_ACCESS_TOKEN_LIFETIME + 1)
    ):
        with pytest.raises(TgtgAPIError):
            client._refresh_token()
        assert old_access_token == client.access_token
        assert old_refresh_token == client.refresh_token


def test_login_empty_fail():
    with pytest.raises(TypeError):
        TgtgClient()._request()


def test_login_empty_token_fail():
    with pytest.raises(TypeError):
        TgtgClient(user_id=1234)._request()


def test_login_empty_user_id_fail():
    with pytest.raises(TypeError):
        TgtgClient(
            access_token="test_token", refresh_token="test_refres_toekn"
        )._request()
