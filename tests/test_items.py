from urllib.parse import urljoin

import pytest
import responses

from tgtg import API_ITEM_ENDPOINT, BASE_URL, TgtgClient
from tgtg.exceptions import TgtgAPIError


@responses.activate
def test_get_items_success():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_ITEM_ENDPOINT),
        json={"items": []},
        status=200,
    )
    client = TgtgClient(access_token="an_access_token", user_id=1234)
    assert client.get_items() == []


@responses.activate
def test_get_items_fail():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_ITEM_ENDPOINT),
        json={"status": 401, "error": "Unauthorized"},
        status=200,
    )
    client = TgtgClient(access_token="an_access_token", user_id=1234)
    with pytest.raises(TgtgAPIError):
        client.get_items()


@responses.activate
def test_get_item_success():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_ITEM_ENDPOINT) + "1",
        json={},
        status=200,
    )
    client = TgtgClient(access_token="an_access_token", user_id=1234)
    assert client.get_item(1) == {}
