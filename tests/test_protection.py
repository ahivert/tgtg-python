import datetime
import time

import pytest
import requests
import responses
from freezegun import freeze_time

from tgtg import API_ITEM_ENDPOINT, BASE_URL, CREATE_ORDER_ENDPOINT, DATADOME_SDK_URL, TgtgClient
from tgtg.exceptions import TgtgAPIError


@pytest.fixture
def protection_client():
    client = TgtgClient(
        user_agent="test-agent",
        access_token="test-access-token",
        refresh_token="test-refresh-token",
        cookie="session_id=keep-me",
        last_time_token_refreshed=datetime.datetime.now(),
    )
    client.session.cookies.set("datadome", "valid-cookie", domain="apptoogoodtogo.com", path="/", secure=True)
    client.session.cookies.set("session_id", "keep-me", domain="apptoogoodtogo.com", path="/")
    return client


@pytest.mark.parametrize("endpoint", [API_ITEM_ENDPOINT, CREATE_ORDER_ENDPOINT + "123"])
def test_unmarked_forbidden_is_not_retried(protection_client, endpoint):
    url = BASE_URL + endpoint
    responses.add(responses.POST, url, json={"error": "forbidden"}, status=403)

    response = protection_client._post(url)

    assert response.status_code == 403
    assert len(responses.calls) == 1
    assert protection_client.session.cookies.get("datadome") == "valid-cookie"
    assert protection_client.session.cookies.get("session_id") == "keep-me"


@pytest.mark.parametrize("header", ["X-DD-B", "X-SF-CC-X-dd-b"])
@pytest.mark.parametrize("status", [403, 429])
def test_protection_block_is_reported_without_retry(protection_client, header, status, caplog):
    from tgtg.exceptions import TgtgProtectionError

    url = BASE_URL + CREATE_ORDER_ENDPOINT + "123"
    responses.add(
        responses.POST,
        url,
        body="private-response-cookie-and-token",
        status=status,
        headers={header: "blocked"},
    )
    protection_client.session.cookies.set("datadome", "other-host", domain="other.example", path="/")
    protection_client.session.cookies.set("datadome", "other-path", domain="apptoogoodtogo.com", path="/unrelated")

    with pytest.raises(TgtgProtectionError) as error:
        protection_client._post(url)

    assert isinstance(error.value, TgtgAPIError)
    assert error.value.args[0] == status
    assert "private-response-cookie-and-token" not in str(error.value)
    assert "private-response-cookie-and-token" not in caplog.text
    assert len(responses.calls) == 1
    assert protection_client.session.cookies.get("session_id") == "keep-me"
    assert protection_client.session.cookies.get("datadome", domain="apptoogoodtogo.com", path="/") is None
    assert protection_client.session.cookies.get("datadome", domain="other.example", path="/") == "other-host"
    assert (
        protection_client.session.cookies.get("datadome", domain="apptoogoodtogo.com", path="/unrelated")
        == "other-path"
    )


def test_protection_marker_on_success_is_not_a_block(protection_client):
    url = BASE_URL + API_ITEM_ENDPOINT
    responses.add(responses.POST, url, json={"items": []}, headers={"X-DD-B": "signal"}, status=200)

    assert protection_client._post(url).json() == {"items": []}
    assert len(responses.calls) == 1


@pytest.mark.parametrize(
    "domain,path,secure,expires,value,url,fetch_expected",
    [
        ("apptoogoodtogo.com", "/", True, None, "valid", BASE_URL, False),
        (".apptoogoodtogo.com", "/api", True, None, "valid", BASE_URL, False),
        ("other.example", "/", True, None, "valid", BASE_URL, True),
        ("apptoogoodtogo.com", "/unrelated", True, None, "valid", BASE_URL, True),
        ("apptoogoodtogo.com", "/ap", True, None, "valid", BASE_URL, True),
        ("apptoogoodtogo.com", "/", True, 1, "expired", BASE_URL, True),
        ("apptoogoodtogo.com", "/", True, None, "", BASE_URL, True),
        ("apptoogoodtogo.com", "/", True, None, "valid", "http://apptoogoodtogo.com/api/", True),
    ],
)
def test_cookie_must_apply_to_request(domain, path, secure, expires, value, url, fetch_expected, monkeypatch):
    client = TgtgClient(user_agent="test-agent")
    client.session.cookies.set("datadome", value, domain=domain, path=path, secure=secure, expires=expires)
    fetched = []
    monkeypatch.setattr(client, "_fetch_datadome_cookie", fetched.append)

    client._ensure_datadome_cookie(url)

    assert fetched == ([url] if fetch_expected else [])


@pytest.mark.parametrize("domain_attribute", ["", "; Domain=.apptoogoodtogo.com"])
def test_saved_cookie_uses_jar_and_does_not_override_rotation(domain_attribute):
    client = TgtgClient(user_agent="test-agent", cookie=f"datadome=saved; Path=/; Secure; HttpOnly{domain_attribute}")
    url = BASE_URL + API_ITEM_ENDPOINT
    responses.add(
        responses.POST,
        url,
        json={"items": []},
        status=200,
        headers={"Set-Cookie": f"datadome=rotated; Path=/; Secure; HttpOnly{domain_attribute}"},
    )
    responses.add(responses.POST, url, json={"items": []}, status=200)

    client._post(url)
    client._post(url)

    assert len(responses.calls) == 2
    assert responses.calls[0].request.headers["Cookie"] == "datadome=saved"
    assert responses.calls[1].request.headers["Cookie"] == "datadome=rotated"
    assert "Cookie" not in client._headers
    assert "Cookie" not in client.session.headers


@freeze_time("2026-10-22 12:00:00")
@pytest.mark.parametrize(
    "attributes,lifetime",
    [("Max-Age=60", 60), ("Expires=Thu, 22 Oct 2026 12:02:00 GMT", 120)],
)
def test_sdk_cookie_preserves_expiration_and_path(attributes, lifetime):
    client = TgtgClient(user_agent="test-agent")
    responses.add(
        responses.POST,
        DATADOME_SDK_URL,
        json={
            "status": 200,
            "cookie": f"datadome=new-cookie; Domain=.apptoogoodtogo.com; Path=/api; Secure; {attributes}",
        },
        status=200,
    )

    client._fetch_datadome_cookie(BASE_URL)

    cookie = next(iter(client.session.cookies))
    assert cookie.name == "datadome"
    assert cookie.value == "new-cookie"
    assert cookie.domain == ".apptoogoodtogo.com"
    assert cookie.path == "/api"
    assert cookie.secure
    assert cookie.expires == int(time.time()) + lifetime


def test_sdk_request_respects_configuration_without_sending_api_credentials():
    client = TgtgClient(
        user_agent="test-agent",
        access_token="private-token",
        cookie="session_id=private-session; Path=/; Secure",
        proxies={"https": "http://proxy.example:8080"},
        timeout=7,
    )
    responses.add(
        responses.POST,
        DATADOME_SDK_URL,
        json={"status": 200, "cookie": "datadome=new-cookie; Path=/; Secure"},
        status=200,
    )

    client._fetch_datadome_cookie(BASE_URL)

    request = responses.calls[0].request
    assert request.req_kwargs["proxies"]["https"] == "http://proxy.example:8080"
    assert request.req_kwargs["timeout"] == 7
    assert "Authorization" not in request.headers
    assert "Cookie" not in request.headers


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"status": 500, "cookie": "private-cookie"},
        {"status": 200, "cookie": None},
        {"status": 200, "cookie": "session_id=private-cookie"},
        {"status": 200, "cookie": "datadome=private-cookie; Max-Age=not-an-integer"},
        {"status": 200, "cookie": "datadome=private-cookie; Max-Age=0"},
        {"status": 200, "cookie": "datadome=private-cookie; Domain=other.example"},
        {"status": 200, "cookie": "datadome=private-cookie; Expires=invalid"},
    ],
)
def test_invalid_sdk_cookie_is_reported_without_leaking_values(payload, caplog):
    client = TgtgClient(user_agent="test-agent")
    responses.add(responses.POST, DATADOME_SDK_URL, json=payload, status=200)

    client._fetch_datadome_cookie(BASE_URL)

    assert "Could not obtain DataDome cookie" in caplog.text
    assert "private-cookie" not in caplog.text
    assert client.session.cookies.get("session_id") is None


def test_sdk_network_failure_is_reported_without_leaking_details(caplog):
    client = TgtgClient(user_agent="test-agent")
    responses.add(responses.POST, DATADOME_SDK_URL, body=requests.Timeout("private-cookie-and-token"))

    client._fetch_datadome_cookie(BASE_URL)

    assert "Could not obtain DataDome cookie (Timeout)" in caplog.text
    assert "private-cookie-and-token" not in caplog.text


def test_order_creation_propagates_protection_error_without_retry(protection_client):
    from tgtg.exceptions import TgtgProtectionError

    url = BASE_URL + CREATE_ORDER_ENDPOINT + "123"
    responses.add(responses.POST, url, status=403, headers={"X-DD-B": "blocked"})

    with pytest.raises(TgtgProtectionError):
        protection_client.create_order("123", 1)

    assert len(responses.calls) == 1


def test_failed_cookie_acquisition_still_allows_api_response(caplog):
    client = TgtgClient(user_agent="test-agent")
    url = BASE_URL + API_ITEM_ENDPOINT
    responses.add(responses.POST, DATADOME_SDK_URL, body=requests.Timeout("private-details"))
    responses.add(
        responses.POST,
        url,
        json={"items": []},
        status=200,
        headers={"Set-Cookie": "datadome=server-cookie; Path=/; Secure"},
    )

    assert client._post(url).json() == {"items": []}
    assert len(responses.calls) == 2
    assert client.session.cookies.get("datadome") == "server-cookie"
    assert "Could not obtain DataDome cookie (Timeout)" in caplog.text
    assert "private-details" not in caplog.text


@pytest.mark.parametrize("status", [403, 500])
def test_sdk_http_failure_is_reported_without_leaking_body(status, caplog):
    client = TgtgClient(user_agent="test-agent")
    responses.add(responses.POST, DATADOME_SDK_URL, body="private-response-body", status=status)

    client._fetch_datadome_cookie(BASE_URL)

    assert "Could not obtain DataDome cookie (HTTPError)" in caplog.text
    assert "private-response-body" not in caplog.text
