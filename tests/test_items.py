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


def test_get_items_custom_user_agent(mocker):
    mocked_post = mocker.patch("requests.post")
    client = TgtgClient(access_token="an_access_token", user_id=1234, user_agent="test")
    client.get_items()
    assert (
        mocked_post.call_args_list[0][1]["headers"]["user-agent"] == client.user_agent
    )


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
        responses.POST, urljoin(BASE_URL, API_ITEM_ENDPOINT) + "1", json={}, status=200
    )
    client = TgtgClient(access_token="an_access_token", user_id=1234)
    assert client.get_item(1) == {}
