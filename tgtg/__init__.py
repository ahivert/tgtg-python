import datetime
import logging
import random
from http import HTTPStatus
from typing import Dict
from urllib.parse import urljoin

import requests

from tgtg.google_play_scraper import get_last_apk_version

from .exceptions import TgtgAPIError, TgtgLoginError, TgtgPollingError

logger = logging.getLogger(__name__)

BASE_URL = "https://apptoogoodtogo.com/api/"
API_ITEM_ENDPOINT = "item/v8/"
AUTH_BY_EMAIL_ENDPOINT = "auth/v3/authByEmail"
AUTH_POLLING_ENDPOINT = "auth/v3/authByRequestPollingId"
SIGNUP_BY_EMAIL_ENDPOINT = "auth/v3/signUpByEmail"
REFRESH_ENDPOINT = "auth/v3/token/refresh"
ACTIVE_ORDER_ENDPOINT = "order/v6/active"
INACTIVE_ORDER_ENDPOINT = "order/v6/inactive"
CREATE_ORDER_ENDPOINT = "order/v7/create/"
ABORT_ORDER_ENDPOINT = "order/v7/{}/abort"
ORDER_STATUS_ENDPOINT = "order/v7/{}/status"
API_BUCKET_ENDPOINT = "discover/v1/bucket"
DEFAULT_APK_VERSION = "22.5.5"
USER_AGENTS = [
    "TGTG/{} Dalvik/2.1.0 (Linux; U; Android 9; Nexus 5 Build/M4B30Z)",
    "TGTG/{} Dalvik/2.1.0 (Linux; U; Android 10; SM-G935F Build/NRD90M)",
    "TGTG/{} Dalvik/2.1.0 (Linux; Android 12; SM-G920V Build/MMB29K)",
]
DEFAULT_ACCESS_TOKEN_LIFETIME = 3600 * 4  # 4 hours
MAX_POLLING_TRIES = 24  # 24 * POLLING_WAIT_TIME = 2 minutes
POLLING_WAIT_TIME = 5  # Seconds


class TgtgClient:
    def __init__(
        self,
        url=BASE_URL,
        email=None,
        access_token=None,
        refresh_token=None,
        user_id=None,
        user_agent=None,
        language="en-UK",
        proxies=None,
        timeout=None,
        last_time_token_refreshed=None,
        access_token_lifetime=DEFAULT_ACCESS_TOKEN_LIFETIME,
        device_type="ANDROID",
        cookie=None,
    ):
        self.base_url = url

        self.email = email

        self.access_token = access_token
        self.refresh_token = refresh_token
        self.user_id = user_id
        self.cookie = cookie

        self.last_time_token_refreshed = last_time_token_refreshed
        self.access_token_lifetime = access_token_lifetime

        self.device_type = device_type

        self.user_agent = user_agent if user_agent else self._get_user_agent()
        self.language = language
        self.proxies = proxies
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers = self._headers

    def _get_user_agent(self):
        try:
            self.version = get_last_apk_version()
        except Exception:
            self.version = DEFAULT_APK_VERSION
            logger.warning("Failed to get last version\n")

        logger.info(f"Using version {self.version}\n")

        return random.choice(USER_AGENTS).format(self.version)

    def _get_url(self, path):
        return urljoin(self.base_url, path)

    @property
    def _headers(self):
        headers = {
            "accept": "application/json",
            "Accept-Encoding": "gzip",
            "accept-language": self.language,
            "content-type": "application/json; charset=utf-8",
            "user-agent": self.user_agent,
        }
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.access_token:
            headers["authorization"] = f"Bearer {self.access_token}"
        return headers

    def _request(self, path, data):
        if path not in [AUTH_BY_EMAIL_ENDPOINT, AUTH_POLLING_ENDPOINT]:
            if not (
                self.access_token
                and self.refresh_token
                and self.user_id
                and self.cookie
            ):
                raise TypeError(
                    "You must provide access_token, refresh_token, user_id and cookie"
                )
            self._refresh_token()

        return self.session.post(
            self._get_url(path),
            json=data,
            headers=self._headers,
            proxies=self.proxies,
            timeout=self.timeout,
        )

    def _refresh_token(self):
        if (
            self.last_time_token_refreshed
            and (datetime.datetime.now() - self.last_time_token_refreshed).seconds
            <= self.access_token_lifetime
        ):
            return

        response = self._request(
            REFRESH_ENDPOINT,
            data={"refresh_token": self.refresh_token},
        )
        if response.status_code == HTTPStatus.OK:
            self.access_token = response.json()["access_token"]
            self.refresh_token = response.json()["refresh_token"]
            self.last_time_token_refreshed = datetime.datetime.now()
            self.cookie = response.headers["Set-Cookie"]
        else:
            raise TgtgAPIError(response.status_code, response.content)

    def get_polling_id(self):
        response = self._request(
            AUTH_BY_EMAIL_ENDPOINT,
            data={
                "device_type": self.device_type,
                "email": self.email,
            },
        )
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            raise TgtgAPIError(
                response.status_code, "Too many requests. Try again later."
            )
        if response.status_code == HTTPStatus.OK:
            first_login_response = response.json()
            if first_login_response["state"] == "TERMS":
                raise TgtgPollingError(
                    f"This email {self.email} is not linked to a tgtg account. "
                    "Please signup with this email first."
                )
            elif first_login_response["state"] == "WAIT":
                return first_login_response["polling_id"]

        raise TgtgLoginError(response.status_code, response.content)

    def validate_polling_id(self, polling_id) -> Dict[str, str]:
        response = self._request(
            AUTH_POLLING_ENDPOINT,
            data={
                "device_type": self.device_type,
                "email": self.email,
                "request_polling_id": polling_id,
            },
        )
        if response.status_code == HTTPStatus.ACCEPTED:
            return None
        if response.status_code == HTTPStatus.OK:
            login_response = response.json()
            return {
                "access_token": login_response["access_token"],
                "refresh_token": login_response["refresh_token"],
                "user_id": login_response["startup_data"]["user"]["user_id"],
                "cookie": response.headers["Set-Cookie"],
            }
        if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
            raise TgtgAPIError(
                response.status_code, "Too many requests. Try again later."
            )
        raise TgtgLoginError(response.status_code, response.content)

    def get_items(
        self,
        *,
        latitude=0.0,
        longitude=0.0,
        radius=21,
        page_size=20,
        page=1,
        discover=False,
        favorites_only=True,
        item_categories=None,
        diet_categories=None,
        pickup_earliest=None,
        pickup_latest=None,
        search_phrase=None,
        with_stock_only=False,
        hidden_only=False,
        we_care_only=False,
    ):
        # fields are sorted like in the app
        data = {
            "user_id": self.user_id,
            "origin": {"latitude": latitude, "longitude": longitude},
            "radius": radius,
            "page_size": page_size,
            "page": page,
            "discover": discover,
            "favorites_only": favorites_only,
            "item_categories": item_categories if item_categories else [],
            "diet_categories": diet_categories if diet_categories else [],
            "pickup_earliest": pickup_earliest,
            "pickup_latest": pickup_latest,
            "search_phrase": search_phrase if search_phrase else None,
            "with_stock_only": with_stock_only,
            "hidden_only": hidden_only,
            "we_care_only": we_care_only,
        }
        response = self._request(
            API_ITEM_ENDPOINT,
            data=data,
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()["items"]
        else:
            raise TgtgAPIError(response.status_code, response.content)

    def get_item(self, item_id):
        response = self._request(
            urljoin(API_ITEM_ENDPOINT, str(item_id)),
            data={"user_id": self.user_id, "origin": None},
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        raise TgtgAPIError(response.status_code, response.content)

    def get_favorites(
        self,
        latitude=0.0,
        longitude=0.0,
        radius=21,
        page_size=50,
        page=0,
    ):
        # fields are sorted like in the app
        data = {
            "origin": {"latitude": latitude, "longitude": longitude},
            "radius": radius,
            "user_id": self.user_id,
            "paging": {"page": page, "size": page_size},
            "bucket": {"filler_type": "Favorites"},
        }
        response = self._request(
            API_BUCKET_ENDPOINT,
            data=data,
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()["mobile_bucket"]["items"]
        raise TgtgAPIError(response.status_code, response.content)

    def set_favorite(self, item_id, is_favorite):
        response = self._request(
            urljoin(API_ITEM_ENDPOINT, f"{item_id}/setFavorite"),
            data={"is_favorite": is_favorite},
        )
        if response.status_code != HTTPStatus.OK:
            raise TgtgAPIError(response.status_code, response.content)

    def create_order(self, item_id, item_count):
        response = self._request(
            urljoin(CREATE_ORDER_ENDPOINT, str(item_id)),
            data={"item_count": item_count},
        )
        if response.status_code != HTTPStatus.OK:
            raise TgtgAPIError(response.status_code, response.content)
        elif response.json()["state"] != "SUCCESS":
            raise TgtgAPIError(response.json()["state"], response.content)
        else:
            return response.json()["order"]

    def get_order_status(self, order_id):
        response = self._request(
            ORDER_STATUS_ENDPOINT.format(order_id),
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            raise TgtgAPIError(response.status_code, response.content)

    def abort_order(self, order_id):
        """Use this when your order is not yet paid"""
        response = self._request(
            ABORT_ORDER_ENDPOINT.format(order_id),
            data={"cancel_reason_id": 1},
        )
        if response.status_code != HTTPStatus.OK:
            raise TgtgAPIError(response.status_code, response.content)
        elif response.json()["state"] != "SUCCESS":
            raise TgtgAPIError(response.json()["state"], response.content)

    def get_active(self):
        response = self._request(
            ACTIVE_ORDER_ENDPOINT,
            data={"user_id": self.user_id},
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        raise TgtgAPIError(response.status_code, response.content)

    def get_inactive(self, page=0, page_size=20):
        response = self._request(
            INACTIVE_ORDER_ENDPOINT,
            data={"paging": {"page": page, "size": page_size}, "user_id": self.user_id},
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        raise TgtgAPIError(response.status_code, response.content)

    def signup_by_email(
        self,
        *,
        email,
        name="",
        country_id="GB",
        newsletter_opt_in=False,
        push_notification_opt_in=True,
    ):
        response = self.session.post(
            self._get_url(SIGNUP_BY_EMAIL_ENDPOINT),
            headers=self._headers,
            json={
                "country_id": country_id,
                "device_type": self.device_type,
                "email": email,
                "name": name,
                "newsletter_opt_in": newsletter_opt_in,
                "push_notification_opt_in": push_notification_opt_in,
            },
            proxies=self.proxies,
            timeout=self.timeout,
        )
        if response.status_code == HTTPStatus.OK:
            self.access_token = response.json()["login_response"]["access_token"]
            self.refresh_token = response.json()["login_response"]["refresh_token"]
            self.last_time_token_refreshed = datetime.datetime.now()
            self.user_id = response.json()["login_response"]["startup_data"]["user"][
                "user_id"
            ]
            return self
        else:
            raise TgtgAPIError(response.status_code, response.content)
