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


def test_get_active_with_session_cookie(client):
    """Test get_active handles session cookies properly."""
    responses.add(
        responses.POST,
        urljoin(BASE_URL, ACTIVE_ORDER_ENDPOINT),
        json={"orders": []},
        status=200,
        headers={"set-cookie": "session_id=abc123; path=/"},
    )
    result = client.get_active()
    assert result == {"orders": []}


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


def test_get_inactive_with_pagination(client):
    """Test get_inactive handles pagination parameters."""
    responses.add(
        responses.POST,
        urljoin(BASE_URL, INACTIVE_ORDER_ENDPOINT),
        json={"orders": [], "paging": {"page": 1, "size": 20}},
        status=200,
    )
    result = client.get_inactive(page=1, page_size=20)
    assert "paging" in result
