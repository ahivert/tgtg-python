from urllib.parse import urljoin

import pytest
import responses

from tgtg import AUTH_POLLING_ENDPOINT, BASE_URL, SIGNUP_BY_EMAIL_ENDPOINT, TgtgClient
from tgtg.exceptions import TgtgAPIError


def test_signup_ok():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, AUTH_POLLING_ENDPOINT),
        json={
            "access_token": "an_access_token",
            "refresh_token": "a_refresh_token",
            "startup_data": {"user": {"user_id": 1234}},
        },
        status=200,
        adding_headers={"set-cookie": "sweet sweet cookie"},
    )
    responses.add(
        responses.POST,
        urljoin(BASE_URL, AUTH_POLLING_ENDPOINT),
        status=202,
    )
    responses.add(
        responses.POST,
        urljoin(BASE_URL, SIGNUP_BY_EMAIL_ENDPOINT),
        json={
            "state": "WAIT",
            "polling_id": "a_polling_id",
        },
        status=200,
    )
    client = TgtgClient()
    client.signup_by_email(email="test@test.com")
    assert client.access_token == "an_access_token"
    assert client.refresh_token == "a_refresh_token"
    assert client.user_id == 1234
    assert client.cookie == "sweet sweet cookie"


def test_signup_fail():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, SIGNUP_BY_EMAIL_ENDPOINT),
        json={"errors": [{"code": "FAILED_SIGN_UP"}]},
        status=400,
    )
    with pytest.raises(TgtgAPIError):
        TgtgClient().signup_by_email(email="test@test.com")
