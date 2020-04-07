import os

import pytest

from tgtg import TgtgClient

from .constants import GLOBAL_PROPERTIES, ITEM_PROPERTIES, STORE_PROPERTIES

pytestmark = pytest.mark.skipif(
    "TGTG_EMAIL" not in os.environ and "TGTG_PASSWORD" not in os.environ,
    reason="Env var `TGTG_EMAIL` and `TGTG_PASSWORD` are absent",
)


def test_e2e_get_items():
    client = TgtgClient(
        email=os.environ["TGTG_EMAIL"], password=os.environ["TGTG_PASSWORD"]
    )
    data = client.get_items(
        favorites_only=False, radius=10, latitude=48.126, longitude=-1.723
    )
    assert len(data) == 100
    assert list(data[0].keys()) == GLOBAL_PROPERTIES


def test_e2e_get_one_item():
    client = TgtgClient(
        email=os.environ["TGTG_EMAIL"], password=os.environ["TGTG_PASSWORD"]
    )
    item_id = "36684i2621241"
    data = client.get_item(item_id)

    assert list(data.keys()) == GLOBAL_PROPERTIES
    assert list(data["item"].keys()) == ITEM_PROPERTIES
    assert list(data["store"].keys()) == STORE_PROPERTIES
    assert data["item"]["item_id"] == item_id
