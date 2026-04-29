import json
from urllib.parse import urljoin

import pytest
import responses

from tgtg import (
    ABORT_ORDER_ENDPOINT,
    BASE_URL,
    CREATE_ORDER_ENDPOINT,
    ORDER_STATUS_ENDPOINT,
)
from tgtg.exceptions import TgtgAPIError


def test_create_order(client):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, urljoin(CREATE_ORDER_ENDPOINT, str(1))),
        json={"state": "SUCCESS", "order": {}},
        status=200,
    )
    order = client.create_order(1, 1)
    order_calls = [
        call for call in responses.calls if CREATE_ORDER_ENDPOINT in call.request.url
    ]
    assert len([order_calls]) == 1
    assert json.loads(order_calls[0].request.body) == {"item_count": 1}
    assert order == {}


def test_create_order_success_with_data(client):
    """Test create_order returns order data when successful."""
    order_data = {
        "state": "SUCCESS",
        "order": {
            "order_id": "order_123",
            "item_count": 2,
            "total_amount": 25.50,
        },
    }
    responses.add(
        responses.POST,
        urljoin(BASE_URL, urljoin(CREATE_ORDER_ENDPOINT, "123")),
        json=order_data,
        status=200,
    )
    result = client.create_order("123", 2)
    assert result == order_data["order"]
    assert result["order_id"] == "order_123"


def test_create_order_failure(client):
    """Test create_order when order state is not SUCCESS."""
    responses.add(
        responses.POST,
        urljoin(BASE_URL, urljoin(CREATE_ORDER_ENDPOINT, "123")),
        json={"state": "FAILURE", "message": "Item sold out"},
        status=200,
    )
    with pytest.raises(TgtgAPIError):
        client.create_order("123", 1)


def test_create_order_non_ok_response(client):
    """Test create_order fails with non-200 response."""
    responses.add(
        responses.POST,
        urljoin(BASE_URL, urljoin(CREATE_ORDER_ENDPOINT, "123")),
        json={},
        status=500,
    )
    with pytest.raises(TgtgAPIError) as exc_info:
        client.create_order("123", 1)
    assert exc_info.value.args[0] == 500


def test_get_order_status(client):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, ORDER_STATUS_ENDPOINT.format(1)),
        json={},
        status=200,
    )
    client.get_order_status(1)
    assert (
        len(
            [
                call
                for call in responses.calls
                if ORDER_STATUS_ENDPOINT.format(1) in call.request.url
            ]
        )
        == 1
    )


def test_get_order_status_success(client):
    """Test get_order_status returns order data when successful."""
    order_status_data = {
        "order_id": "order_123",
        "state": "COLLECTED",
        "item_count": 1,
    }
    responses.add(
        responses.POST,
        urljoin(BASE_URL, ORDER_STATUS_ENDPOINT.format("order_123")),
        json=order_status_data,
        status=200,
    )
    result = client.get_order_status("order_123")
    assert result == order_status_data


def test_get_order_status_fail(client):
    """Test get_order_status returns error on bad response."""
    responses.add(
        responses.POST,
        urljoin(BASE_URL, ORDER_STATUS_ENDPOINT.format("order_123")),
        json={},
        status=400,
    )
    with pytest.raises(TgtgAPIError):
        client.get_order_status("order_123")


def test_abort_order(client):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, ABORT_ORDER_ENDPOINT.format(1)),
        json={"state": "SUCCESS"},
        status=200,
    )
    client.abort_order(1)
    assert (
        len(
            [
                call
                for call in responses.calls
                if ABORT_ORDER_ENDPOINT.format(1) in call.request.url
            ]
        )
        == 1
    )


def test_abort_order_success(client):
    """Test abort_order returns None when successful."""
    responses.add(
        responses.POST,
        urljoin(BASE_URL, ABORT_ORDER_ENDPOINT.format("order_123")),
        json={"state": "SUCCESS"},
        status=200,
    )
    result = client.abort_order("order_123")
    assert result is None


def test_abort_order_fail(client):
    """Test abort_order returns error when state is not SUCCESS."""
    responses.add(
        responses.POST,
        urljoin(BASE_URL, ABORT_ORDER_ENDPOINT.format("order_123")),
        json={"state": "FAILURE", "message": "Cannot abort paid order"},
        status=200,
    )
    with pytest.raises(TgtgAPIError):
        client.abort_order("order_123")
