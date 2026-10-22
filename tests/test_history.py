import json

import pytest
import responses

from tgtg.exceptions import TgtgAPIError


HISTORY_URL = "https://apptoogoodtogo.com/api/order/v8"


def test_get_order_history_first_page(client):
    history = {
        "current_time": "2026-10-22T12:00:00Z",
        "has_more": True,
        "next_page_year": 2026,
        "next_page_month": 9,
        "magic_bag_count": 2,
        "orders_per_month": [{"year": 2026, "month": 10, "magic_bag_count": 2, "orders": []}],
    }
    responses.add(responses.POST, HISTORY_URL, json=history, status=200)

    assert client.get_order_history() == history

    calls = [call for call in responses.calls if call.request.url == HISTORY_URL]
    assert len(calls) == 1
    assert json.loads(calls[0].request.body) == {
        "paging": {"size": 20, "next_page_year": None, "next_page_month": None}
    }


def test_get_order_history_next_page(client):
    history = {"orders_per_month": [], "has_more": False}
    responses.add(responses.POST, HISTORY_URL, json=history, status=200)

    assert client.get_order_history(page_size=50, next_page_year=2025, next_page_month=12) == history

    calls = [call for call in responses.calls if call.request.url == HISTORY_URL]
    assert len(calls) == 1
    assert json.loads(calls[0].request.body) == {"paging": {"size": 50, "next_page_year": 2025, "next_page_month": 12}}


@pytest.mark.parametrize("status", [400, 429, 500])
def test_get_order_history_fail(client, status):
    responses.add(responses.POST, HISTORY_URL, json={}, status=status)

    with pytest.raises(TgtgAPIError) as error:
        client.get_order_history()

    assert error.value.args[0] == status
