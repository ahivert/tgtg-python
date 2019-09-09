from urllib.parse import urljoin

import pytest
import responses

from tgtg import BASE_URL, LOGIN_ENDPOINT, TgtgClient


@responses.activate
def test_init_client_with_email_password_success():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, LOGIN_ENDPOINT),
        json={"access_token": "an_access_token", "user_id": 1234, "language": "en-US"},
        status=200,
    )
    client = TgtgClient(email="test@test.com", password="test")
    assert client.access_token == "an_access_token"
    assert client.user_id == 1234


def test_init_client_with_token_user_id_success():
    client = TgtgClient(access_token="an_access_token", user_id=1234)
    assert client.access_token == "an_access_token"
    assert client.user_id == 1234


def test_init_client_empty_fail():
    with pytest.raises(ValueError):
        TgtgClient()


def test_init_client_empty_email_fail():
    with pytest.raises(ValueError):
        TgtgClient(password="test")


def test_init_client_empty_token_fail():
    with pytest.raises(ValueError):
        TgtgClient(user_id=1234)
