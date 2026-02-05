# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Unofficial Python client for the [TooGoodToGo](https://toogoodtogo.com) API. Published on PyPI as `tgtg`. Python 3.9+. Licensed under GPL-3.0.

## Commands

```bash
# Install dependencies (requires poetry)
# Option 1: if pipx is available
pipx install poetry

# Option 2: via venv (if pipx/poetry not available)
python3 -m venv .venv
source .venv/bin/activate
pip install poetry

# Then install project deps
poetry install

# Run all tests (with coverage)
make test              # or: poetry run pytest

# Run a single test file
poetry run pytest tests/test_login.py

# Run a single test function
poetry run pytest tests/test_login.py::test_login_with_tokens

# Run linting (black, isort, flake8)
make lint              # or: poetry run pre-commit run -a

# Build and publish to PyPI
make publish
```

## Code Style

- Formatter: **Black**
- Import sorting: **isort** (profile: black)
- Linter: **flake8** (max-line-length: 119, max-complexity: 10)
- All enforced via pre-commit hooks

## Architecture

The entire library is a single class `TgtgClient` in `tgtg/__init__.py` (~500 lines). There are no subpackages or complex abstractions.

### Key components

- **`tgtg/__init__.py`** - `TgtgClient` class plus all API endpoint constants. Every public method calls `self.login()` first, which handles token refresh automatically. The client uses `requests.Session` for HTTP, with Android user-agent spoofing. All API calls go through the central `_post()` method which handles DataDome cookie management and 403 retry logic.
- **`tgtg/exceptions.py`** - Three exception types: `TgtgLoginError`, `TgtgAPIError`, `TgtgPollingError`.
- **`tgtg/google_play_scraper.py`** - Scrapes the Google Play Store page to get the current TooGoodToGo APK version for user-agent strings. Falls back to `DEFAULT_APK_VERSION`.

### DataDome bot protection

TooGoodToGo uses DataDome for bot protection. The client handles this by:

1. Fetching a `datadome` cookie from `https://api-sdk.datadome.co/sdk/` before API requests, mimicking the Android app's DataDome SDK integration (device fingerprint parameters like model, OS version, screen size).
2. The `_post()` method automatically ensures a DataDome cookie is present. On 403, it invalidates the cookie and retries with a fresh one.
3. The `_generate_datadome_cid()` helper creates random 120-char client IDs matching DataDome's expected format.
4. VPN/datacenter IPs are frequently blocked by DataDome regardless of cookie validity — residential IPs work best.

### Authentication flow

1. Email-based login sends a request to `auth/v5/authByEmail`
2. User receives a PIN code via email
3. Client submits PIN via `auth/v5/authByRequestPin` to complete authentication
4. Fallback: client can also poll `auth/v5/authByRequestPollingId` (legacy link-click flow)
5. On success, stores `access_token`, `refresh_token`, and `cookie`
6. Tokens auto-refresh after `access_token_lifetime` (default 4 hours)

### API versions in use

Auth endpoints use `v5`, item endpoints use `v8`, order endpoints use `v8`, token refresh uses `v1`, favorites use `v1`, discover uses `v1`.

## Testing

- Framework: **pytest** with **responses** library for HTTP mocking
- Coverage: branch coverage enabled, configured in `setup.cfg` (`addopts = --cov=tgtg`)
- Tests in `tests/` use fixtures from `conftest.py` that mock auth/refresh endpoints
- `tests/constants.py` contains expected API response property lists and fake token credentials
- `test_api.py` contains integration tests marked `@pytest.mark.withoutresponses` that hit the real API (requires `TGTG_EMAIL` env var)
- Time-dependent tests use **freezegun** for mocking `datetime.datetime.now()`
