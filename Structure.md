# Project structure

[README (English)](README.md) · [中文说明](README.zh-CN.md)

## The shape of it

Two layers, deliberately kept apart:

```
tgtg/                        the library: how to talk to the API
examples/watch_favorites.py  the policy: when to talk to it, and what to do when refused
```

The library answers *how do I ask TooGoodToGo for my favourites*. The watcher answers
*how often may I ask, what do I do when the answer is a captcha, and where do the
credentials live*. Nearly every day-to-day adjustment belongs in the watcher; the library
only changes when the API does.

```
tgtg-python-master/
├── tgtg/                            Library (upstream code plus the fixes below)
│   ├── __init__.py            644   TgtgClient, endpoint constants, DataDome handling
│   ├── exceptions.py           10   TgtgLoginError, TgtgAPIError, TgtgPollingError
│   └── google_play_scraper.py  13   Scrapes the current APK version for the user agent
├── examples/
│   └── watch_favorites.py     692   The watcher: polling, notifications, restraint
├── tests/                           101 tests
├── docs/
│   └── api-reference.md       518   Endpoint response shapes, kept from upstream
├── .venv/                           Local virtualenv (gitignored)
├── pyproject.toml                   Dependencies, ruff and pytest configuration
├── Makefile                         make test, make lint
├── README.md · README.zh-CN.md      Usage
└── Structure.md                     This file
```

Secrets and runtime state live outside the repository, so that an editor, a stray commit
or a shared folder cannot pick them up:

```
~/.config/tgtg/credentials.json   access token, refresh token, cookie   (mode 0600)
~/.config/tgtg/state.json         device identity, daily counters        (mode 0600)
~/.config/tgtg/watcher.lock       single-instance lock
```

## The library: `tgtg/__init__.py`

One class, no subpackages. Every public method follows the same shape: call `login()`,
`_post()`, check the status, return JSON or raise `TgtgAPIError`.

| Lines | What lives there |
| --- | --- |
| [17-74](tgtg/__init__.py#L17-L74) | Endpoint constants and `DEVICE_PROFILES` |
| [81-103](tgtg/__init__.py#L81-L103) | Cookie parsing and device-profile helpers |
| [107-145](tgtg/__init__.py#L107-L145) | `TgtgClient.__init__` — the whole configuration surface |
| [170-201](tgtg/__init__.py#L170-L201) | Header and `Cookie` construction |
| [206-325](tgtg/__init__.py#L206-L325) | DataDome: seeding, fetching, dropping, and `_post` retry |
| [327-437](tgtg/__init__.py#L327-L437) | Token refresh and the email/PIN login flow |
| [439-644](tgtg/__init__.py#L439-L644) | The API surface: items, favourites, orders, signup |

### DataDome, in order of what happens

TooGoodToGo fronts its API with [DataDome](https://datadome.co). Getting through it is
most of the complexity in this file.

1. **Seed** ([`_seed_datadome_cookie`](tgtg/__init__.py#L206)) — if stored credentials
   already carry a `datadome` cookie, put it in the session jar. A cookie the server
   issued and that has already carried authenticated calls is worth more than a newly
   minted one, and skipping the handshake is one less bot signal per process.
2. **Fetch** ([`_fetch_datadome_cookie`](tgtg/__init__.py#L235)) — otherwise POST a device
   fingerprint to the DataDome SDK endpoint, mimicking what the Android app sends. The
   model, OS version and screen size come from the profile that matches the current user
   agent, so the two cannot contradict each other.
3. **Merge** ([`_cookie_header`](tgtg/__init__.py#L186)) — build the `Cookie` header by
   hand, combining stored credentials with the jar. This is not optional: `cookielib`
   refuses to add jar cookies when a request already carries a `Cookie` header, so
   without this the datadome cookie is silently never sent.
4. **Retry** ([`_post`](tgtg/__init__.py#L303)) — on `403`, forget the refused cookie,
   fetch a fresh one and try once more.

Note that `403` is overloaded: TooGoodToGo returns it for ordinary auth failures
(`{"errors":[{"code":"UNAUTHORIZED"}]}`) *and* DataDome returns it for a captcha challenge
(a body containing a `geo.captcha-delivery.com` URL). They need completely different
responses, so the watcher tells them apart rather than treating every `403` the same.

### Authentication

1. `auth/v5/authByEmail` returns a `polling_id`.
2. The user receives a PIN by email and enters it; `auth/v5/authByRequestPin` completes it.
3. Pressing enter without a PIN falls back to the older click-the-link polling flow.
4. Tokens are refreshed through `token/v1/refresh`.

API versions currently in use: auth `v5`, items `v9`, orders `v8`, favourites `v1`,
discover `v1`, token refresh `v1`, manufacturer items `v2`.

## The watcher: `examples/watch_favorites.py`

| Lines | What lives there |
| --- | --- |
| [68-81](examples/watch_favorites.py#L68-L81) | Tunable constants |
| [84-213](examples/watch_favorites.py#L84-L213) | Logging, redaction, credential I/O, locking, time windows |
| [216-250](examples/watch_favorites.py#L216-L250) | `Notifier` — ntfy, Bark, Telegram |
| [253-311](examples/watch_favorites.py#L253-L311) | Item formatting, and classifying an API error |
| [314-352](examples/watch_favorites.py#L314-L352) | `--diagnose` and `--reset-identity` |
| [355-583](examples/watch_favorites.py#L355-L583) | `Watcher` — the loop, the budget, the circuit breaker |
| [585-692](examples/watch_favorites.py#L585-L692) | Argument parsing and `main()` |

### Why the restraint exists

A naive polling loop gets an account flagged, and then retries itself into a deeper hole.
Each of these measures is a response to something that actually went wrong:

- **Circuit breaker** ([`handle_api_error`](examples/watch_favorites.py#L503)) — a captcha
  challenge doubles the backoff (300s, 600s, 1200s…) and the fifth consecutive one stops
  the process instead of retrying forever. Retrying during a challenge only extends it.
- **Single-instance lock** ([`acquire_lock`](examples/watch_favorites.py#L167)) — several
  processes polling one account at once is what triggered the worst block during
  development. The second watcher now refuses to start.
- **Daily budget and active hours** — polling around the clock is itself a signal. The
  budget is a hard ceiling; the window keeps requests inside plausible waking hours.
- **Persistent device identity** ([`_build_client`](examples/watch_favorites.py#L386)) — a
  new user agent and correlation id per launch makes one device look like a fleet of fresh
  ones. A stored user agent that matches no device profile is replaced, because otherwise
  it would silently contradict the fingerprint sent to DataDome.
- **JWT-aware refresh** ([`_token_freshness`](examples/watch_favorites.py#L373)) —
  `token/v1/refresh` is the most heavily protected endpoint. Reading `exp` out of the
  access token means going there only when it is genuinely about to expire, rather than on
  a fixed four-hour timer while the token still has 30 hours left.
- **Redaction** ([`redact`](examples/watch_favorites.py#L88)) — every error body and
  exception passes through a filter that strips JWTs and long opaque tokens before they
  can reach a log file or terminal scrollback.
- **Atomic private writes** ([`_write_private_json`](examples/watch_favorites.py#L109)) —
  credentials are created through `os.open(..., 0o600)` and then `os.replace`d, so they are
  never briefly world-readable and a crash cannot leave a truncated file.

### The polling loop

[`Watcher.run`](examples/watch_favorites.py#L546) repeats:

1. Outside the active window? Sleep until it opens.
2. Daily budget spent? Sleep until midnight.
3. Poll. Notify on a `0 → in stock` edge only, so a restart does not re-announce
   everything and a bag that stays in stock is not announced twice.
4. Reserve, if `--reserve` is set and the daily cap allows it.
5. Persist rotated tokens and counters, then sleep `interval ± jitter`.

Failures route through `handle_api_error`, which returns a delay — or `None`, meaning stop.

## Tests

101 tests, no network unless `TGTG_EMAIL` is set.

| File | Covers |
| --- | --- |
| `test_login.py` | Login, token refresh, the day-boundary refresh bug |
| `test_datadome.py` | Cookie merging, reuse, 403 refetch, fingerprint consistency, handshake errors |
| `test_items.py` · `test_order.py` · `test_active.py` · `test_signup.py` | API surface |
| `test_watcher_credentials.py` | File modes, atomic writes, redaction, path resolution, migration |
| `test_watcher_safety.py` | Circuit breaker, budget rollover, active hours, locking, identity, JWT expiry |
| `test_api.py` | Integration tests against the real API; skipped without `TGTG_EMAIL` |
| `test_apk.py` | The Google Play version scrape (hits the network) |

```bash
make test                                  # everything, with branch coverage
./.venv/bin/pytest tests/test_datadome.py  # one file
./.venv/bin/pytest -k circuit              # by name
```

## Where to change what

| You want to | Go to |
| --- | --- |
| Poll more or less often | `--interval`, or [watch_favorites.py:68](examples/watch_favorites.py#L68) |
| Change the watching hours | `--active-hours`, or [:70](examples/watch_favorites.py#L70) |
| Loosen the request ceiling | `--max-polls-per-day`, or [:71](examples/watch_favorites.py#L71) |
| Change backoff or the give-up threshold | [:73-75](examples/watch_favorites.py#L73-L75) |
| Add a notification backend | [`Notifier`](examples/watch_favorites.py#L216) |
| Change what a notification says | [`describe`](examples/watch_favorites.py#L276) |
| Add an API endpoint | [`tgtg/__init__.py`](tgtg/__init__.py#L439) alongside the others |
| Adjust the device fingerprint | [`DEVICE_PROFILES`](tgtg/__init__.py#L38) — keep UA and payload in sync |

Run `make test` afterwards. The suite covers the circuit breaker, the budget, the time
windows and credential permissions, so it will catch most ways of weakening the restraints
by accident.
