from urllib.parse import urljoin

import pytest
import responses

from tgtg import (
    ACTIVE_ORDER_ENDPOINT,
    BASE_URL,
    DATADOME_SDK_URL,
    REFRESH_ENDPOINT,
    TgtgClient,
    _parse_cookie_header,
)

FRESH_DATADOME = "datadome=FRESH_DD; Max-Age=31536000; Domain=.apptoogoodtogo.com; Path=/; Secure"


@pytest.fixture(scope="function")
def datadome_response():
    responses.add(
        responses.POST,
        DATADOME_SDK_URL,
        json={"status": 200, "cookie": FRESH_DATADOME},
        status=200,
    )


def _build_client(cookie):
    responses.add(
        responses.POST,
        urljoin(BASE_URL, REFRESH_ENDPOINT),
        json={"access_token": "an_access_token", "refresh_token": "a_refresh_token"},
        status=200,
        adding_headers={"set-cookie": "session_id=abc123; Path=/; Secure"},
    )
    responses.add(
        responses.POST,
        urljoin(BASE_URL, ACTIVE_ORDER_ENDPOINT),
        json={"orders": []},
        status=200,
    )
    return TgtgClient(access_token="access_token", refresh_token="refresh_token", cookie=cookie)


def _cookie_headers_sent():
    return [call.request.headers.get("Cookie") for call in responses.calls if BASE_URL in call.request.url]


def test_datadome_cookie_is_sent_alongside_stored_cookie(datadome_response):
    """The jar is skipped by cookielib once a Cookie header exists, so datadome must be merged in."""
    client = _build_client("session_id=abc123; Path=/; Secure")
    client.get_active()

    headers = _cookie_headers_sent()
    assert headers, "no request reached the tgtg API"
    for header in headers:
        assert "datadome=FRESH_DD" in header
        assert "session_id=abc123" in header
        assert "Path" not in header


def test_stored_cookie_still_sent_without_datadome():
    """With no datadome cookie available the stored credentials are still sent, minus attributes."""
    client = _build_client("session_id=abc123; Path=/; Secure; HttpOnly")
    client.get_active()

    headers = _cookie_headers_sent()
    assert headers, "no request reached the tgtg API"
    for header in headers:
        assert header == "session_id=abc123"


def test_parse_cookie_header_drops_attributes_and_splits_joined_headers():
    raw = "a=1; Path=/; Expires=Wed, 21 Oct 2015 07:28:00 GMT, b=2; Secure; HttpOnly"
    assert _parse_cookie_header(raw) == {"a": "1", "b": "2"}
