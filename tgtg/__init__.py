import json
import random
from urllib.parse import urljoin

import requests

from .exceptions import TgtgAPIError, TgtgLoginError

BASE_URL = "https://apptoogoodtogo.com/"
API_ITEM_ENDPOINT = "api/item/v1/"
LOGIN_ENDPOINT = "index.php/api_tgtg/login"


class TgtgClient:
    """
    """

    def __init__(
        self, url=BASE_URL, email=None, password=None, access_token=None, user_id=None
    ):
        self.base_url = url

        auth_with_token = access_token is not None and user_id is not None
        auth_with_email = email is not None and password is not None

        if not auth_with_email and not auth_with_token:
            raise ValueError(
                "You must fill email and password or access_token and user_id"
            )

        self.access_token = access_token
        self.user_id = user_id
        if auth_with_email:
            login_response = self._login(email, password)
            self.access_token = login_response["access_token"]
            self.user_id = login_response["user_id"]
            self.language = login_response["language"]

    @property
    def item_url(self):
        return urljoin(self.base_url, API_ITEM_ENDPOINT)

    @property
    def login_url(self):
        return urljoin(self.base_url, LOGIN_ENDPOINT)

    @property
    def headers(self):
        headers = {
            "user-agent": random.choice(
                [
                    "TGTG/19.6.1 Dalvik/2.1.0 (Linux; U; Android 6.0.1; Nexus 5 Build/M4B30Z)",
                    "TGTG/19.6.1 Dalvik/2.1.0 (Linux; U; Android 7.0; SM-G935F Build/NRD90M)",
                    "TGTG/19.6.1 Dalvik/2.1.0 (Linux; Android 6.0.1; SM-G920V Build/MMB29K) ",
                ]
            )
        }
        if self.access_token:
            headers["authorization"] = f"Bearer {self.access_token}"
        return headers

    def _login(self, email, password):
        response = requests.post(
            self.login_url,
            headers=self.headers,
            data={"email": email, "password": password},
        )
        if response.status_code == 200:
            login_response = json.loads(response.content)
            return login_response
        raise TgtgLoginError(response.content)

    def get_items(
        self,
        discover=False,
        favorites_only=True,
        hidden_only=False,
        latitude=0.0,
        longitude=0.0,
        page=1,
        page_size=100,
        radius=0.0,
        with_stock_only=False,
    ):
        """
        """
        data = {
            "discover": discover,
            "favorites_only": favorites_only,
            "hidden_only": hidden_only,
            "origin": {
                "latLng": {"a": latitude, "b": longitude},
                "latitude": latitude,
                "longitude": longitude,
            },
            "page": page,
            "page_size": page_size,
            "radius": radius,
            "user_id": self.user_id,
            "with_stock_only": with_stock_only,
        }
        response = requests.post(self.item_url, headers=self.headers, json=data)
        if response.status_code == 200:
            return json.loads(response.content)["items"]
        else:
            TgtgAPIError(response.content)
