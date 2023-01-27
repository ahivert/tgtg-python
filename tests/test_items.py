from urllib.parse import urljoin

import pytest
import responses

from tgtg import API_ITEM_ENDPOINT, BASE_URL, TgtgClient
from tgtg.exceptions import TgtgAPIError

from .constants import tgtg_client_fake_tokens


def test_get_items_success(refresh_tokens_response):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_ITEM_ENDPOINT),
        json={"items": []},
        status=200,
    )
    client = TgtgClient(**tgtg_client_fake_tokens)
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


def test_get_items_fail(refresh_tokens_response):
    responses.add(
        responses.POST, urljoin(BASE_URL, API_ITEM_ENDPOINT), json={}, status=400
    )
    client = TgtgClient(**tgtg_client_fake_tokens)
    with pytest.raises(TgtgAPIError):
        client.get_items()


def test_get_item_success(refresh_tokens_response):
    responses.add(
        responses.POST, urljoin(BASE_URL, API_ITEM_ENDPOINT) + "1", json={}, status=200
    )
    client = TgtgClient(**tgtg_client_fake_tokens)
    assert client.get_item(1) == {}
    assert (
        len([call for call in responses.calls if API_ITEM_ENDPOINT in call.request.url])
        == 1
    )


def test_get_item_fail(refresh_tokens_response):
    responses.add(
        responses.POST, urljoin(BASE_URL, API_ITEM_ENDPOINT) + "1", json={}, status=400
    )
    client = TgtgClient(**tgtg_client_fake_tokens)
    with pytest.raises(TgtgAPIError):
        client.get_item(1)


def test_set_favorite(refresh_tokens_response):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_ITEM_ENDPOINT) + "1/setFavorite",
        json={},
        status=200,
    )
    client = TgtgClient(**tgtg_client_fake_tokens)
    assert client.set_favorite(1, True) is None
    assert (
        len([call for call in responses.calls if API_ITEM_ENDPOINT in call.request.url])
        == 1
    )


def test_set_favorite_fail(refresh_tokens_response):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_ITEM_ENDPOINT) + "1/setFavorite",
        json={},
        status=400,
    )
    client = TgtgClient(**tgtg_client_fake_tokens)
    with pytest.raises(TgtgAPIError):
        client.set_favorite(1, True)
