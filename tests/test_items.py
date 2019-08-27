from urllib.parse import urljoin

import responses

from tgtg import API_ITEM_ENDPOINT, BASE_URL, TgtgClient


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
