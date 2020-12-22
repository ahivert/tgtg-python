from urllib.parse import urljoin

import pytest
import responses

from tgtg import BASE_URL, LOGIN_ENDPOINT


@pytest.fixture(scope="function")
def login_response():
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
