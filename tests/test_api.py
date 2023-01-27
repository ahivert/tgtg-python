import os

import pytest

from tgtg import TgtgClient

from .constants import GLOBAL_PROPERTIES, ITEM_PROPERTIES, STORE_PROPERTIES


@pytest.mark.skipif(
    not os.environ.get("TGTG_EMAIL"),
    reason="Env var `TGTG_EMAIL` absent",
)
@pytest.mark.withoutresponses
class TestLoginRequired:
    def test_get_items(self):
        client = TgtgClient(email=os.environ["TGTG_EMAIL"])
        data = client.get_items(
            favorites_only=False, radius=10, latitude=48.126, longitude=-1.723
        )
        assert len(data) == 20
        for property in GLOBAL_PROPERTIES:
            assert property in data[0]

    def test_get_one_item(self):
        client = TgtgClient(email=os.environ["TGTG_EMAIL"])
        item_id = "36684"
        data = client.get_item(item_id)

        print(data.keys())
        print(data["item"].keys())
        print(data["store"].keys())

        for property in GLOBAL_PROPERTIES:
            assert property in data
        for property in ITEM_PROPERTIES:
            assert property in data["item"]
        for property in STORE_PROPERTIES:
            assert property in data["store"]

        assert data["item"]["item_id"] == item_id
