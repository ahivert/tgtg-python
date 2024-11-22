from urllib.parse import urljoin

import pytest
import responses

from tgtg import (
    AUTH_BY_EMAIL_ENDPOINT,
    AUTH_POLLING_ENDPOINT,
    BASE_URL,
    REFRESH_ENDPOINT,
    TgtgClient,
)

from .constants import tgtg_client_fake_tokens


@pytest.fixture(scope="function")
def auth_by_email_response():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, AUTH_BY_EMAIL_ENDPOINT),
        json={"state": ""},
        status=200,
    )


@pytest.fixture(scope="function")
def auth_polling_response():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, AUTH_POLLING_ENDPOINT),
        json={
            "access_token": "an_access_token",
            "refresh_token": "a_refresh_token"
        },
        status=200,
    )


@pytest.fixture(scope="function")
def refresh_tokens_response():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, REFRESH_ENDPOINT),
        json={
            "access_token": "an_access_token",
            "refresh_token": "a_refresh_token",
        },
        status=200,
        adding_headers={"set-cookie": "sweet sweet cookie"},
    )


@pytest.fixture(scope="function")
def client(refresh_tokens_response):
    yield TgtgClient(**tgtg_client_fake_tokens)
