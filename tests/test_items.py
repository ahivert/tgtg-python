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
    assert len(responses.calls) == 1


@responses.activate
def test_get_items_custom_user_agent():
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_ITEM_ENDPOINT),
        json={"items": []},
        status=200,
    )
    custom_user_agent = "test"
    client = TgtgClient(
        access_token="an_access_token", user_id=1234, user_agent=custom_user_agent
    )
    client.get_items()
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers["user-agent"] == custom_user_agent


@responses.activate
def test_get_items_fail():
    responses.add(
        responses.POST, urljoin(BASE_URL, API_ITEM_ENDPOINT), json={}, status=400
    )
    client = TgtgClient(access_token="an_access_token", user_id=1234)
    with pytest.raises(TgtgAPIError):
        client.get_items()


@responses.activate
def test_get_item_success():
    responses.add(
        responses.POST, urljoin(BASE_URL, API_ITEM_ENDPOINT) + "1", json={}, status=200
    )
    client = TgtgClient(access_token="an_access_token", user_id=1234)
    assert client.get_item(1) == {}
    assert len(responses.calls) == 1
