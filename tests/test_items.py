from urllib.parse import urljoin

import pytest
import responses

from tgtg import (
    API_BUCKET_ENDPOINT,
    API_ITEM_ENDPOINT,
    BASE_URL,
    FAVORITE_ITEM_ENDPOINT,
    MANUFACTURER_ITEM_ENDPOINT,
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


def test_get_item_success_with_data(client):
    """Test get_item returns proper data when successful."""
    item_data = {
        "item_id": "123",
        "name": "Test Item",
        "items_available": 5,
    }
    responses.add(
        responses.POST,
        urljoin(BASE_URL, "item/v8/123"),
        json=item_data,
        status=200,
    )
    result = client.get_item("123")
    assert result == item_data


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


def test_get_favorites_with_items(client):
    """Test get_favorites returns items when present."""
    favorites_data = {
        "mobile_bucket": {
            "items": [
                {
                    "item_id": "1",
                    "name": "Item 1",
                    "items_available": 3,
                },
                {
                    "item_id": "2",
                    "name": "Item 2",
                    "items_available": 0,
                },
            ]
        }
    }
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_BUCKET_ENDPOINT),
        json=favorites_data,
        status=200,
    )
    favorites = client.get_favorites()
    assert len(favorites) == 2
    assert favorites[0]["item_id"] == "1"


def test_get_favorites_empty_response(client):
    """Test get_favorites handles empty bucket response."""
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_BUCKET_ENDPOINT),
        json={},
        status=200,
    )
    favorites = client.get_favorites()
    assert favorites == []


def test_get_favorites_nested_items(client):
    """Test get_favorites extracts items from nested response."""
    favorites_data = {
        "mobile_bucket": {
            "items": [
                {"item_id": "1", "name": "First"},
                {"item_id": "2", "name": "Second"},
                {"item_id": "3", "name": "Third"},
            ]
        }
    }
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_BUCKET_ENDPOINT),
        json=favorites_data,
        status=200,
    )
    favorites = client.get_favorites()
    assert len(favorites) == 3
    assert all("item_id" in item for item in favorites)


def test_get_favorites_non_ok_response(client):
    """Test get_favorites fails with non-200 response."""
    responses.add(
        responses.POST,
        urljoin(BASE_URL, API_BUCKET_ENDPOINT),
        json={},
        status=500,
    )
    with pytest.raises(TgtgAPIError) as exc_info:
        client.get_favorites()
    assert exc_info.value.args[0] == 500


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


def test_set_favorite_success(client):
    """Test set_favorite returns None when successful."""
    responses.add(
        responses.POST,
        urljoin(BASE_URL, FAVORITE_ITEM_ENDPOINT.format("item_123")),
        json={},
        status=200,
    )
    result = client.set_favorite("item_123", True)
    assert result is None


def test_set_favorite_fail(client):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, FAVORITE_ITEM_ENDPOINT.format(1)),
        json={},
        status=400,
    )
    with pytest.raises(TgtgAPIError):
        client.set_favorite(1, True)


def test_set_favorite_non_ok_response(client):
    """Test set_favorite fails with non-200 response."""
    responses.add(
        responses.POST,
        urljoin(BASE_URL, FAVORITE_ITEM_ENDPOINT.format("item_123")),
        json={},
        status=500,
    )
    with pytest.raises(TgtgAPIError) as exc_info:
        client.set_favorite("item_123", True)
    assert exc_info.value.args[0] == 500


def test_get_manufacturing_items_fail(client):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, MANUFACTURER_ITEM_ENDPOINT),
        json={},
        status=400,
    )
    with pytest.raises(TgtgAPIError):
        client.get_manufacturer_items()


def test_get_manufacturing_items_success(client):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, MANUFACTURER_ITEM_ENDPOINT),
        json={},
        status=200,
    )
    assert client.get_manufacturer_items() == {}
    assert (
        len(
            [
                call
                for call in responses.calls
                if MANUFACTURER_ITEM_ENDPOINT in call.request.url
            ]
        )
        == 1
    )
