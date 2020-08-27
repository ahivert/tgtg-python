import os

import pytest

from tgtg import TgtgClient

from .constants import GLOBAL_PROPERTIES, ITEM_PROPERTIES, STORE_PROPERTIES


def test_get_all_business_auth_not_required():
    client = TgtgClient()
    data = client.get_all_business()
    assert len(data) > 0


@pytest.mark.skipif(
    not (os.environ.get("TGTG_EMAIL") or os.environ.get("TGTG_PASSWORD")),
    reason="Env var `TGTG_EMAIL` and `TGTG_PASSWORD` are absent",
)
class TestLoginRequired:
    def test_get_items(self):
        client = TgtgClient(
            email=os.environ["TGTG_EMAIL"], password=os.environ["TGTG_PASSWORD"]
        )
        data = client.get_items(
            favorites_only=False, radius=10, latitude=48.126, longitude=-1.723
        )
        assert len(data) == 20
        assert all(prop in data[0] for prop in GLOBAL_PROPERTIES)

    def test_get_one_item(self):
        client = TgtgClient(
            email=os.environ["TGTG_EMAIL"], password=os.environ["TGTG_PASSWORD"]
        )
        item_id = "36684"
        data = client.get_item(item_id)

        assert all(prop in data for prop in GLOBAL_PROPERTIES)
        assert all(prop in data["item"] for prop in ITEM_PROPERTIES)
        assert all(prop in data["store"] for prop in STORE_PROPERTIES)
        assert data["item"]["item_id"] == item_id
