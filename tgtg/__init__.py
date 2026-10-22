import datetime
import logging
import random
import sys
import time
import uuid
from http import HTTPStatus
from http.cookiejar import http2time
from http.cookies import CookieError, SimpleCookie
from urllib.parse import urljoin, urlsplit

import requests

from tgtg.google_play_scraper import get_last_apk_version

from .exceptions import TgtgAPIError, TgtgLoginError, TgtgPollingError, TgtgProtectionError

logger = logging.getLogger(__name__)

BASE_URL = "https://apptoogoodtogo.com/api/"
API_ITEM_ENDPOINT = "item/v9/"
FAVORITE_ITEM_ENDPOINT = "user/favorite/v1/{}/update"
AUTH_BY_EMAIL_ENDPOINT = "auth/v5/authByEmail"
AUTH_POLLING_ENDPOINT = "auth/v5/authByRequestPollingId"
AUTH_BY_REQUEST_PIN_ENDPOINT = "auth/v5/authByRequestPin"
SIGNUP_BY_EMAIL_ENDPOINT = "auth/v5/signUpByEmail"
REFRESH_ENDPOINT = "token/v1/refresh"
ACTIVE_ORDER_ENDPOINT = "order/v8/active"
INACTIVE_ORDER_ENDPOINT = "order/v8/inactive"
ORDER_HISTORY_ENDPOINT = "order/v8"
CREATE_ORDER_ENDPOINT = "order/v8/create/"
ABORT_ORDER_ENDPOINT = "order/v8/{}/abort"
ORDER_STATUS_ENDPOINT = "order/v8/{}/status"
API_BUCKET_ENDPOINT = "discover/v1/bucket"
MANUFACTURER_ITEM_ENDPOINT = "manufactureritem/v2"
DATADOME_SDK_URL = "https://api-sdk.datadome.co/sdk/"


DEFAULT_APK_VERSION = "24.11.0"
USER_AGENTS = [
    "TGTG/{} Dalvik/2.1.0 (Linux; U; Android 9; Nexus 5 Build/M4B30Z)",
    "TGTG/{} Dalvik/2.1.0 (Linux; U; Android 10; SM-G935F Build/NRD90M)",
    "TGTG/{} Dalvik/2.1.0 (Linux; Android 12; SM-G920V Build/MMB29K)",
]
DEFAULT_ACCESS_TOKEN_LIFETIME = 3600 * 4  # 4 hours
MAX_POLLING_TRIES = 24  # 24 * POLLING_WAIT_TIME = 2 minutes
POLLING_WAIT_TIME = 5  # Seconds


def _generate_datadome_cid():
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789~_"
    return "".join(random.choice(chars) for _ in range(120))


class TgtgClient:
    def __init__(
        self,
        url=BASE_URL,
        email=None,
        access_token=None,
        refresh_token=None,
        user_agent=None,
        language="en-GB",
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
        self.cookie = cookie

        self.last_time_token_refreshed = last_time_token_refreshed
        self.access_token_lifetime = access_token_lifetime
        self.correlation_id = str(uuid.uuid4())

        self.device_type = device_type

        self.user_agent = user_agent if user_agent else self._get_user_agent()
        self.language = language
        self.proxies = proxies
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers = self._headers
        for morsel in SimpleCookie(cookie or "").values():
            self._store_cookie(morsel)

    def _get_user_agent(self):
        try:
            self.version = get_last_apk_version()
        except Exception:
            self.version = DEFAULT_APK_VERSION
            sys.stdout.write("Failed to get last version\n")

        sys.stdout.write(f"Using version {self.version}\n")

        return random.choice(USER_AGENTS).format(self.version)

    def _get_url(self, path):
        return urljoin(self.base_url, path)

    def get_credentials(self):
        self.login()
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "cookie": self.cookie,
        }

    @property
    def _headers(self):
        headers = {
            "accept": "application/json",
            "Accept-Encoding": "gzip",
            "accept-language": self.language,
            "content-type": "application/json; charset=utf-8",
            "user-agent": self.user_agent,
            "x-correlation-id": self.correlation_id,
        }
        if self.access_token:
            headers["authorization"] = f"Bearer {self.access_token}"
        return headers

    @property
    def _already_logged(self):
        return bool(self.access_token and self.refresh_token)

    def _store_cookie(self, morsel):
        origin = urlsplit(self.base_url)
        if not origin.hostname:
            raise ValueError("The API URL must have a hostname")
        domain = morsel["domain"].lstrip(".").lower() or origin.hostname
        if origin.hostname != domain and not origin.hostname.endswith("." + domain):
            raise ValueError("Cookie domain does not match the API host")
        expires = None
        if morsel["max-age"]:
            expires = int(time.time()) + int(morsel["max-age"])
        elif morsel["expires"]:
            expires = http2time(morsel["expires"])
            if expires is None:
                raise ValueError("Invalid cookie expiration")
        cookie = requests.cookies.create_cookie(
            morsel.key,
            morsel.value,
            domain=f".{domain}" if morsel["domain"] else domain,
            path=morsel["path"] or "/",
            secure=origin.scheme == "https" or bool(morsel["secure"]),
            expires=expires,
        )
        cookie.domain_specified = bool(morsel["domain"])
        self.session.cookies.set_cookie(cookie)

    def _fetch_datadome_cookie(self, request_url):
        """Fetch a DataDome cookie from the SDK endpoint, mimicking the Android app."""
        cid = _generate_datadome_cid()
        apk_version = getattr(self, "version", DEFAULT_APK_VERSION)
        params = {
            "camera": '{"auth":"true", "info":"{\\"front\\":\\"2000x1500\\",\\"back\\":\\"5472x3648\\"}"}',
            "cid": cid,
            "ddk": "1D42C2CA6131C526E09F294FE96F94",
            "ddv": "3.0.4",
            "ddvc": apk_version,
            "events": '[{"id":1,"message":"response validation","source":"sdk","date":'
            + str(int(time.time() * 1000))
            + "}]",
            "inte": "android-java-okhttp",
            "mdl": "Pixel 7 Pro",
            "os": "Android",
            "osn": "UPSIDE_DOWN_CAKE",
            "osr": "14",
            "osv": "34",
            "request": request_url,
            "screen_d": "3.5",
            "screen_x": "1440",
            "screen_y": "3120",
            "ua": self.user_agent,
        }
        try:
            r = requests.post(
                DATADOME_SDK_URL,
                data=params,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "*/*",
                    "User-Agent": self.user_agent,
                    "Accept-Encoding": "gzip, deflate, br",
                },
                proxies=self.proxies,
                timeout=self.timeout if self.timeout is not None else 10,
            )
            r.raise_for_status()
            data = r.json()
            if not isinstance(data, dict) or data.get("status") != 200 or not isinstance(data.get("cookie"), str):
                raise ValueError("Invalid cookie response")
            cookies = SimpleCookie(data["cookie"])
            if "datadome" not in cookies or not cookies["datadome"].value:
                raise ValueError("Missing protection cookie")
            self._store_cookie(cookies["datadome"])
            if not any(self._datadome_cookies(request_url)):
                raise ValueError("Protection cookie does not apply to the request")
        except (requests.RequestException, ValueError, TypeError, CookieError) as exc:
            logger.warning("Could not obtain DataDome cookie (%s).", type(exc).__name__)

    def _datadome_cookies(self, request_url):
        request = requests.Request("POST", request_url).prepare()
        for cookie in self.session.cookies:
            if cookie.name == "datadome" and cookie.value:
                jar = requests.cookies.RequestsCookieJar()
                jar.set_cookie(cookie)
                if requests.cookies.get_cookie_header(jar, request):
                    yield cookie

    def _ensure_datadome_cookie(self, request_url):
        if not any(self._datadome_cookies(request_url)):
            self._fetch_datadome_cookie(request_url)

    def _post(self, url, **kwargs):
        """Send once: replaying a POST can duplicate a state-changing operation."""
        self._ensure_datadome_cookie(url)
        response = self.session.post(
            url,
            headers=self._headers,
            proxies=self.proxies,
            timeout=self.timeout,
            **kwargs,
        )
        if response.status_code >= 400 and any(
            response.headers.get(header) for header in ("X-DD-B", "X-SF-CC-X-dd-b")
        ):
            for cookie in list(self._datadome_cookies(url)):
                self.session.cookies.clear(cookie.domain, cookie.path, cookie.name)
            raise TgtgProtectionError(
                response.status_code,
                "Bot protection blocked the request. User verification may be required; the request was not retried.",
            )
        return response

    def _refresh_token(self):
        if (
            self.last_time_token_refreshed
            and (datetime.datetime.now() - self.last_time_token_refreshed).seconds <= self.access_token_lifetime
        ):
            return

        response = self._post(
            self._get_url(REFRESH_ENDPOINT),
            json={"refresh_token": self.refresh_token},
        )
        if response.status_code == HTTPStatus.OK:
            self.access_token = response.json()["access_token"]
            self.refresh_token = response.json()["refresh_token"]
            self.last_time_token_refreshed = datetime.datetime.now()
            self.cookie = response.headers["Set-Cookie"]
        else:
            raise TgtgAPIError(response.status_code, response.content)

    def login(self):
        if not (self.email or self.access_token and self.refresh_token and self.cookie):
            raise TypeError("You must provide at least email or access_token, refresh_token and cookie")
        if self._already_logged:
            self._refresh_token()
        else:
            response = self._post(
                self._get_url(AUTH_BY_EMAIL_ENDPOINT),
                json={
                    "device_type": self.device_type,
                    "email": self.email,
                },
            )
            if response.status_code == HTTPStatus.OK:
                first_login_response = response.json()
                if first_login_response["state"] == "TERMS":
                    raise TgtgPollingError(
                        f"This email {self.email} is not linked to a tgtg account. "
                        "Please signup with this email first."
                    )
                elif first_login_response["state"] == "WAIT":
                    self.start_polling(first_login_response["polling_id"])
                else:
                    raise TgtgLoginError(response.status_code, response.content)
            else:
                if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                    raise TgtgAPIError(response.status_code, "Too many requests. Try again later.")
                else:
                    raise TgtgLoginError(response.status_code, response.content)

    def start_polling(self, polling_id):
        sys.stdout.write("Check your email for a login PIN code.\n")
        pin = input("Enter PIN from email: ").strip()
        if pin:
            return self._auth_by_pin(polling_id, pin)

        for _ in range(MAX_POLLING_TRIES):
            response = self._post(
                self._get_url(AUTH_POLLING_ENDPOINT),
                json={
                    "device_type": self.device_type,
                    "email": self.email,
                    "request_polling_id": polling_id,
                },
            )
            if response.status_code == HTTPStatus.ACCEPTED:
                sys.stdout.write(
                    "Check your mailbox on PC to continue... "
                    "(Opening email on mobile won't work, if you have installed tgtg app.)\n"
                )
                time.sleep(POLLING_WAIT_TIME)
                continue
            elif response.status_code == HTTPStatus.OK:
                sys.stdout.write("Logged in!\n")
                login_response = response.json()
                self.access_token = login_response["access_token"]
                self.refresh_token = login_response["refresh_token"]
                self.last_time_token_refreshed = datetime.datetime.now()
                self.cookie = response.headers["Set-Cookie"]
                return
            else:
                if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                    raise TgtgAPIError(response.status_code, "Too many requests. Try again later.")
                else:
                    raise TgtgLoginError(response.status_code, response.content)

        raise TgtgPollingError(f"Max retries ({MAX_POLLING_TRIES * POLLING_WAIT_TIME} seconds) reached. Try again.")

    def _auth_by_pin(self, polling_id, pin):
        response = self._post(
            self._get_url(AUTH_BY_REQUEST_PIN_ENDPOINT),
            json={
                "device_type": self.device_type,
                "email": self.email,
                "request_pin": pin,
                "request_polling_id": polling_id,
            },
        )
        if response.status_code == HTTPStatus.OK:
            sys.stdout.write("Logged in!\n")
            login_response = response.json()
            self.access_token = login_response["access_token"]
            self.refresh_token = login_response["refresh_token"]
            self.last_time_token_refreshed = datetime.datetime.now()
            self.cookie = response.headers.get("Set-Cookie", "")
            return
        else:
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
        self.login()

        # fields are sorted like in the app
        data = {
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
        response = self._post(
            self._get_url(API_ITEM_ENDPOINT),
            json=data,
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()["items"]
        else:
            raise TgtgAPIError(response.status_code, response.content)

    def get_item(self, item_id):
        self.login()
        response = self._post(
            urljoin(self._get_url(API_ITEM_ENDPOINT), str(item_id)),
            json={"origin": None},
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            raise TgtgAPIError(response.status_code, response.content)

    def get_favorites(
        self,
        latitude=0.0,
        longitude=0.0,
        radius=21,
        page_size=50,
        page=0,
    ):
        self.login()

        # fields are sorted like in the app
        data = {
            "origin": {"latitude": latitude, "longitude": longitude},
            "radius": radius,
            "paging": {"page": page, "size": page_size},
            "bucket": {"filler_type": "Favorites"},
        }
        response = self._post(
            self._get_url(API_BUCKET_ENDPOINT),
            json=data,
        )
        if response.status_code == HTTPStatus.OK:
            return response.json().get("mobile_bucket", {}).get("items", [])
        else:
            raise TgtgAPIError(response.status_code, response.content)

    def set_favorite(self, item_id, is_favorite):
        self.login()
        response = self._post(
            self._get_url(FAVORITE_ITEM_ENDPOINT.format(item_id)),
            json={"is_favorite": is_favorite},
        )
        if response.status_code != HTTPStatus.OK:
            raise TgtgAPIError(response.status_code, response.content)

    def create_order(self, item_id, item_count):
        self.login()

        response = self._post(
            urljoin(self._get_url(CREATE_ORDER_ENDPOINT), str(item_id)),
            json={"item_count": item_count},
        )
        if response.status_code != HTTPStatus.OK:
            raise TgtgAPIError(response.status_code, response.content)
        elif response.json()["state"] != "SUCCESS":
            raise TgtgAPIError(response.json()["state"], response.content)
        else:
            return response.json()["order"]

    def get_order_status(self, order_id):
        self.login()

        response = self._post(
            self._get_url(ORDER_STATUS_ENDPOINT.format(order_id)),
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            raise TgtgAPIError(response.status_code, response.content)

    def abort_order(self, order_id):
        """Use this when your order is not yet paid"""
        self.login()

        response = self._post(
            self._get_url(ABORT_ORDER_ENDPOINT.format(order_id)),
            json={"cancel_reason_id": 1},
        )
        if response.status_code != HTTPStatus.OK:
            raise TgtgAPIError(response.status_code, response.content)
        elif response.json()["state"] != "SUCCESS":
            raise TgtgAPIError(response.json()["state"], response.content)
        else:
            return

    def signup_by_email(
        self,
        *,
        email,
        name="",
        country_id="GB",
        newsletter_opt_in=False,
        push_notification_opt_in=True,
    ):
        response = self._post(
            self._get_url(SIGNUP_BY_EMAIL_ENDPOINT),
            json={
                "country_id": country_id,
                "device_type": self.device_type,
                "email": email,
                "name": name,
                "newsletter_opt_in": newsletter_opt_in,
                "push_notification_opt_in": push_notification_opt_in,
            },
        )
        if response.status_code == HTTPStatus.OK:
            self.access_token = response.json()["login_response"]["access_token"]
            self.refresh_token = response.json()["login_response"]["refresh_token"]
            self.last_time_token_refreshed = datetime.datetime.now()

            return self
        else:
            raise TgtgAPIError(response.status_code, response.content)

    def get_active(self):
        self.login()
        response = self._post(
            self._get_url(ACTIVE_ORDER_ENDPOINT),
            json={},
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            raise TgtgAPIError(response.status_code, response.content)

    def get_inactive(self, page=0, page_size=20):
        self.login()
        response = self._post(
            self._get_url(INACTIVE_ORDER_ENDPOINT),
            json={"paging": {"page": page, "size": page_size}},
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            raise TgtgAPIError(response.status_code, response.content)

    def get_order_history(self, *, page_size=20, next_page_year=None, next_page_month=None):
        """Return monthly order history, preserving the server's pagination cursors."""
        self.login()
        response = self._post(
            self._get_url(ORDER_HISTORY_ENDPOINT),
            json={
                "paging": {
                    "size": page_size,
                    "next_page_year": next_page_year,
                    "next_page_month": next_page_month,
                }
            },
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            raise TgtgAPIError(response.status_code, response.content)

    def get_manufacturer_items(self):
        self.login()

        data = {
            "display_types_accepted": ["LIST"],
            "element_types_accepted": [
                "ITEM",
                "NPS",
                "TEXT",
                "DUO_ITEMS",
                "MANUFACTURER_STORY_CARD",
            ],
            "action_types_accepted": [],
        }
        response = self._post(
            self._get_url(MANUFACTURER_ITEM_ENDPOINT),
            json=data,
        )
        if response.status_code == HTTPStatus.OK:
            return response.json()
        else:
            raise TgtgAPIError(response.status_code, response.content)
