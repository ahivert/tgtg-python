import json
from urllib.parse import urljoin

import responses

from tgtg import (
    ABORT_ORDER_ENDPOINT,
    BASE_URL,
    CREATE_ORDER_ENDPOINT,
    ORDER_STATUS_ENDPOINT,
)


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


def get_order_status(client):
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
