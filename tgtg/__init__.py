import json
import random
from urllib.parse import urljoin

import requests

from .exceptions import TgtgAPIError, TgtgLoginError

BASE_URL = "https://apptoogoodtogo.com/"
API_ITEM_ENDPOINT = "api/item/v5/"
LOGIN_ENDPOINT = "index.php/api_tgtg/login"
ALL_BUSINESS_ENDPOINT = "index.php/api_tgtg/list_all_business_map_v5_gz"


class TgtgClient:
    def __init__(
        self, url=BASE_URL, email=None, password=None, access_token=None, user_id=None
    ):
        self.base_url = url
        self.email = email
        self.password = password
        self.access_token = access_token
        self.user_id = user_id
        self.language = None

    @property
    def item_url(self):
        return urljoin(self.base_url, API_ITEM_ENDPOINT)

    @property
    def all_business_url(self):
        return urljoin(self.base_url, ALL_BUSINESS_ENDPOINT)

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

    @property
    def already_logged(self):
        return self.access_token and self.user_id

    def _login(self):
        if self.already_logged:
            return

        if not self.email or not self.password:
            raise ValueError(
                "You must fill email and password or access_token and user_id"
            )

        response = requests.post(
            self.login_url,
            headers=self.headers,
            data={"email": self.email, "password": self.password},
        )
        login_response = json.loads(response.content)
        if login_response["status_code"] == 1:
            self.access_token = login_response["access_token"]
            self.user_id = login_response["user_id"]
            self.language = login_response["language"]
        else:
            raise TgtgLoginError(response.content)

    def get_all_business(self):
        response = requests.get(self.all_business_url)
        try:
            return response.json()["info"]
        except KeyError:
            raise TgtgAPIError(response.content)

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
        we_care_only=False,
        with_stock_only=False,
    ):
        self._login()
        data = {
            "discover": discover,
            "favorites_only": favorites_only,
            "hidden_only": hidden_only,
            "origin": {"latitude": latitude, "longitude": longitude},
            "page": page,
            "page_size": page_size,
            "radius": radius,
            "user_id": self.user_id,
            "we_care_only": we_care_only,
            "with_stock_only": with_stock_only,
        }
        response = requests.post(self.item_url, headers=self.headers, json=data)
        try:
            return response.json()["items"]
        except KeyError:
            raise TgtgAPIError(response.content)

    def get_item(self, item_id):
        self._login()
        response = requests.post(
            urljoin(self.item_url, str(item_id)),
            headers=self.headers,
            json={"user_id": self.user_id},
        )
        try:
            return response.json()
        except KeyError:
            raise TgtgAPIError
