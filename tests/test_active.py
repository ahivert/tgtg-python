from urllib.parse import urljoin

import pytest
import responses

from tgtg import ACTIVE_ORDER_ENDPOINT, BASE_URL, INACTIVE_ORDER_ENDPOINT
from tgtg.exceptions import TgtgAPIError


def test_get_active_success(client):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, ACTIVE_ORDER_ENDPOINT),
        json={"orders": []},
        status=200,
        headers={"set-cookie": "session_id=12345; a=b; c=d"},
    )
    assert client.get_active()["orders"] == []
    assert (
        len(
            [
                call
                for call in responses.calls
                if ACTIVE_ORDER_ENDPOINT in call.request.url
            ]
        )
        == 1
    )


def test_get_active_fail(client):
    responses.add(
        responses.POST, urljoin(BASE_URL, ACTIVE_ORDER_ENDPOINT), json={}, status=400
    )
    with pytest.raises(TgtgAPIError):
        client.get_active()


def test_get_inactive_success(client):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, INACTIVE_ORDER_ENDPOINT),
        json={"orders": []},
        status=200,
    )
    assert client.get_inactive()["orders"] == []
    assert (
        len(
            [
                call
                for call in responses.calls
                if INACTIVE_ORDER_ENDPOINT in call.request.url
            ]
        )
        == 1
    )


def test_get_inactive_fail(client):
    responses.add(
        responses.POST, urljoin(BASE_URL, INACTIVE_ORDER_ENDPOINT), json={}, status=400
    )
    with pytest.raises(TgtgAPIError):
        client.get_inactive()
