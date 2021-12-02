from urllib.parse import urljoin

import pytest
import responses

from tgtg import BASE_URL, SIGNUP_BY_EMAIL_ENDPOINT, TgtgClient
from tgtg.exceptions import TgtgAPIError


def test_signup_ok():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, SIGNUP_BY_EMAIL_ENDPOINT),
        json={
            "login_response": {
                "access_token": "an_access_token",
                "refresh_token": "a_refresh_token",
                "startup_data": {"user": {"user_id": 1234}},
            }
        },
        status=200,
    )
    client = TgtgClient().signup_by_email(email="test@test.com")
    assert client.access_token == "an_access_token"
    assert client.refresh_token == "a_refresh_token"
    assert client.user_id == 1234


def test_signup_fail():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, SIGNUP_BY_EMAIL_ENDPOINT),
        json={"errors": [{"code": "FAILED_SIGN_UP"}]},
        status=400,
    )
    with pytest.raises(TgtgAPIError):
        TgtgClient().signup_by_email(email="test@test.com")
