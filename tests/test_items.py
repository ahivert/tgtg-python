from urllib.parse import urljoin

import pytest
import responses

from tgtg import (
    API_BUCKET_ENDPOINT,
    API_ITEM_ENDPOINT,
    BASE_URL,
    FAVORITE_ITEM_ENDPOINT,
    TgtgClient,
)
from tgtg.exceptions import TgtgAPIError

from .constants import tgtg_client_fake_tokens


def test_get_items_success(client):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_ITEM_ENDPOINT),
        json={"items": []},
        status=200,
    )
    assert client.get_items() == []
    assert (
        len([call for call in responses.calls if API_ITEM_ENDPOINT in call.request.url])
        == 1
    )


def test_get_items_custom_user_agent(refresh_tokens_response):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_ITEM_ENDPOINT),
        json={"items": []},
        status=200,
    )
    custom_user_agent = "test"
    client = TgtgClient(user_agent=custom_user_agent, **tgtg_client_fake_tokens)
    client.get_items()
    assert (
        len([call for call in responses.calls if API_ITEM_ENDPOINT in call.request.url])
        == 1
    )
    for call in responses.calls:
        assert call.request.headers["user-agent"] == custom_user_agent


def test_get_items_fail(client):
    responses.add(
        responses.POST, urljoin(BASE_URL, API_ITEM_ENDPOINT), json={}, status=400
    )
    with pytest.raises(TgtgAPIError):
        client.get_items()


def test_get_item_success(client):
    responses.add(
        responses.POST, urljoin(BASE_URL, API_ITEM_ENDPOINT) + "1", json={}, status=200
    )
    assert client.get_item(1) == {}
    assert (
        len([call for call in responses.calls if API_ITEM_ENDPOINT in call.request.url])
        == 1
    )


def test_get_item_fail(client):
    responses.add(
        responses.POST, urljoin(BASE_URL, API_ITEM_ENDPOINT) + "1", json={}, status=400
    )
    with pytest.raises(TgtgAPIError):
        client.get_item(1)


@pytest.mark.parametrize(
    "data,expected", [({}, []), ({"mobile_bucket": {"items": []}}, [])]
)
def test_get_favorites(client, data, expected):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_BUCKET_ENDPOINT),
        json=data,
        status=200,
    )
    favorites = client.get_favorites()
    assert favorites == expected
    assert (
        len(
            [
                call
                for call in responses.calls
                if API_BUCKET_ENDPOINT in call.request.url
            ]
        )
        == 1
    )


def test_set_favorite(client):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, FAVORITE_ITEM_ENDPOINT.format(1)),
        json={},
        status=200,
    )
    assert client.set_favorite(1, True) is None
    assert (
        len(
            [
                call
                for call in responses.calls
                if FAVORITE_ITEM_ENDPOINT.format(1) in call.request.url
            ]
        )
        == 1
    )


def test_set_favorite_fail(client):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, FAVORITE_ITEM_ENDPOINT.format(1)),
        json={},
        status=400,
    )
    with pytest.raises(TgtgAPIError):
        client.set_favorite(1, True)
