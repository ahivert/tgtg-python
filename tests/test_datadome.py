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


def test_stored_datadome_cookie_is_reused(datadome_response):
    """A datadome cookie the server already blessed beats minting a new one on every start."""
    client = _build_client("Datadome=STORED_DD; Path=/")
    client.get_active()

    header = _cookie_headers_sent()[0]
    assert "STORED_DD" in header
    assert "FRESH_DD" not in header
    assert not [call for call in responses.calls if DATADOME_SDK_URL in call.request.url], (
        "the SDK handshake should be skipped when a stored cookie is available"
    )


def test_datadome_cookie_is_refetched_after_403(datadome_response):
    """A 403 invalidates the stored cookie and the retry must carry the fresh one."""
    client = _build_client("Datadome=STORED_DD; Path=/")
    url = client._get_url(ACTIVE_ORDER_ENDPOINT)
    responses.replace(responses.POST, url, json={}, status=403)
    responses.add(responses.POST, url, json={"orders": []}, status=200)

    client._post(url, json={})

    first, retry = _cookie_headers_sent()[0], _cookie_headers_sent()[1]
    assert "STORED_DD" in first
    assert "datadome=FRESH_DD" in retry
    assert "STORED_DD" not in retry


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


def test_refused_datadome_cookie_is_not_kept(datadome_response):
    """A cookie that got a 403 must be dropped from credentials, not seeded again next start."""
    client = _build_client("session_id=abc123; Datadome=BURNED_DD")
    url = client._get_url(ACTIVE_ORDER_ENDPOINT)
    responses.replace(responses.POST, url, json={}, status=403)
    responses.add(responses.POST, url, json={"orders": []}, status=200)

    client._post(url, json={})

    assert "BURNED_DD" not in client.cookie
    assert "session_id=abc123" in client.cookie


@pytest.mark.parametrize(
    "registered,expected",
    [
        ({"json": {"status": 200, "cookie": FRESH_DATADOME}, "status": 200}, "datadome=FRESH_DD"),
        ({"json": {}, "status": 403}, "refused the handshake: HTTP 403"),
        ({"json": {}, "status": 429}, "refused the handshake: HTTP 429"),
        ({"json": {"status": 403}, "status": 200}, "returned no cookie (status 403)"),
        ({"body": "not json", "status": 200}, "unreadable response"),
    ],
)
def test_datadome_handshake_failures_say_why(registered, expected, capsys):
    """A silent 'Failed to fetch DataDome cookie' hides exactly the detail that matters."""
    responses.add(responses.POST, DATADOME_SDK_URL, **registered)
    client = TgtgClient(access_token="at", refresh_token="rt", user_agent="ua")

    client._fetch_datadome_cookie("https://apptoogoodtogo.com/api/item/v9/")

    output = capsys.readouterr().out
    if expected.startswith("datadome="):
        assert client.session.cookies.get("datadome") == "FRESH_DD"
    else:
        assert expected in output
