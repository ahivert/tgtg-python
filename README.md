# tgtg-python (hardened fork)

[中文说明](README.zh-CN.md) · [Project structure](Structure.md)

An unofficial Python client for the [TooGoodToGo](https://toogoodtogo.com) API, plus a
watcher script that tells you the moment a surprise bag appears in your favourites.

This is a fork of [ahivert/tgtg-python](https://github.com/ahivert/tgtg-python). The
library keeps the upstream interface; what changed is that several bugs around DataDome
bot protection and token refresh are fixed, and there is now a watcher built for running
unattended for weeks without getting the account flagged.

Python 3.9+ · GPL-3.0

## What this is good for

- **Watching favourites** and getting a push notification when a bag goes on sale.
- **Reserving** a bag automatically so nobody takes it while you reach for your phone.
- **Reading** items, stores, orders and order history through the API.

## What it cannot do

- **Pay for an order.** The client can create a reservation (`state: RESERVED`), but
  payment goes through the mobile SDKs and is not implemented. You finish the purchase in
  the phone app, within the few minutes the reservation lasts.
- **Solve a DataDome captcha.** When TooGoodToGo's bot protection decides to challenge
  you, every call comes back `403` with a `geo.captcha-delivery.com` URL and nothing in
  this process can answer it. The only cures are waiting and behaving less like a bot.
- **Run from a VPN or a cloud server.** DataDome scores datacenter and VPN ranges as high
  risk. Use a residential connection: home broadband or a phone hotspot.

This talks to an undocumented API. Automating it likely breaks TooGoodToGo's terms of
service, and the account risk is yours.

## Install

```bash
pipx install uv
uv sync --all-extras
```

Or with a plain virtualenv:

```bash
python -m venv .venv
./.venv/bin/pip install -e ".[dev]"
```

## Watcher quick start

```bash
# 1. Log in once. Asks for the PIN that TooGoodToGo mails you.
./.venv/bin/python examples/watch_favorites.py --login --email you@example.com

# 2. See what is in your favourites, and whether anything is in stock right now.
./.venv/bin/python examples/watch_favorites.py --list

# 3. Watch, and push to a private ntfy topic when a bag shows up.
./.venv/bin/python examples/watch_favorites.py --notify https://ntfy.sh/your-random-topic

# 4. Once notifications are proven, let it reserve for you.
./.venv/bin/python examples/watch_favorites.py --notify https://ntfy.sh/your-random-topic --reserve 1
```

Credentials are written to `~/.config/tgtg/credentials.json` with mode `0600`, never into
the repository. Notifications go to [ntfy](https://ntfy.sh), Bark or Telegram; with no
notification flag everything is simply logged.

### Commands

| Command | What it does |
| --- | --- |
| `--login --email <address>` | Interactive PIN login; stores credentials |
| `--list` | Print every favourite with its current stock, then exit |
| `--diagnose` | One anonymous probe: is this network getting through at all? |
| `--reset-identity` | Forget the stored device fingerprint, keep the tokens |
| `--once` | Poll a single time and exit |
| (no command) | Watch continuously |

`--diagnose` is the one to reach for when things break. It sends a single request with a
brand new identity and no credentials, so it separates *this network is blocked* from
*this account is blocked* — a distinction you cannot make from a failing `--list`.

### Tuning

| Flag | Default | Notes |
| --- | --- | --- |
| `--interval` | `120` | Seconds between polls |
| `--jitter` | `30` | Random ± seconds, so requests are not metronomic |
| `--active-hours` | `7-23` | Local-time window; `0-24` never sleeps; `22-6` wraps overnight |
| `--max-polls-per-day` | `600` | Hard ceiling; on reaching it the watcher sleeps until midnight |
| `--max-reserves-per-day` | `3` | Cap on automatic reservations |
| `--store <text>` | — | Only watch matching stores; repeatable |

**Check the arithmetic before lowering `--interval`.** A 16-hour window at 60 seconds is
960 polls, which blows through the 600/day budget by mid-afternoon and leaves you blind
during the evening drop. Narrow the window instead — it costs fewer requests *and* polls
faster where it matters:

```bash
# 5 hours at 60s = 300 polls, half the budget, twice the speed
./.venv/bin/python examples/watch_favorites.py --active-hours 16-21 --interval 60 \
    --notify https://ntfy.sh/your-random-topic
```

### Running unattended

```bash
caffeinate -i ./.venv/bin/python examples/watch_favorites.py --notify https://ntfy.sh/your-topic
```

`caffeinate -i` stops the Mac idling to sleep, which would otherwise pause polling
silently. Closing a laptop lid sleeps regardless. `tmux` or `nohup` keep the process alive
when you close the terminal; neither helps with sleep.

## Using the library directly

```python
from tgtg import TgtgClient

# First run: prompts for the PIN mailed to you
client = TgtgClient(email="you@example.com")
credentials = client.get_credentials()

# Later runs: build from stored credentials
client = TgtgClient(**credentials)

for item in client.get_favorites():
    print(item["display_name"], item["items_available"])
```

Every public method calls `login()` first, which refreshes the access token when needed.
See [docs/api-reference.md](docs/api-reference.md) for endpoint-by-endpoint response
shapes, and [Structure.md](Structure.md) for how the pieces fit together.

## What was fixed in this fork

Library (`tgtg/`):

- **The DataDome cookie was never sent on authenticated calls.** `cookielib` skips the
  cookie jar entirely when a request already carries a `Cookie` header, so every request
  built from stored credentials silently dropped the cookie the client had just fetched.
- **A token older than a day was never refreshed.** `timedelta.seconds` discards whole
  days, so a 24h-old token looked one second fresh.
- **`login()` demanded a cookie**, which is not a credential — a freshly reset client
  simply fetches a new one.
- **A new device on every launch.** The user agent, correlation id and DataDome cookie are
  now reusable across restarts instead of being minted per process.
- **The user agent contradicted the fingerprint.** The client claimed an Android 9 Nexus 5
  while telling DataDome it was a Pixel 7 Pro on Android 14. Device profiles now keep the
  two in sync.
- **Handshake failures were silent.** `Failed to fetch DataDome cookie` now says whether
  it was an HTTP 403, a timeout, or an unreadable response.

Watcher (`examples/watch_favorites.py`) adds restraint that a bare polling loop lacks: a
circuit breaker that stops instead of retrying into a deeper block, a single-instance
lock, a daily request budget, an active-hours window, and credential handling that keeps
secrets out of the repository and tokens out of log output.

## Development

```bash
make test     # pytest with branch coverage
make lint     # ruff check + ruff format --check
```

101 tests. The suite mocks HTTP with [responses](https://github.com/getsentry/responses)
and freezes time with [freezegun](https://github.com/spulec/freezegun); no test touches
the real API unless `TGTG_EMAIL` is set.

## Credits

Upstream library by [Anthony Hivert](https://github.com/ahivert). Licensed GPL-3.0; see
[LICENCE](LICENCE).
