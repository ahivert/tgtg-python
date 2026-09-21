"""Watch your TooGoodToGo favourites and get pinged when a surprise bag shows up.

The client cannot pay for an order (see README), so the useful workflow is:
this script spots the bag, optionally reserves it, and you finish the payment
in the phone app within the few minutes the reservation lasts.

Run it from a residential IP (home broadband, phone hotspot). DataDome scores
datacenter and VPN ranges as high risk, and once it decides to challenge you it
answers every call with a captcha interstitial no cookie can satisfy.

This talks to an unofficial API; automating it likely breaks TooGoodToGo's terms
of service and the account risk is yours.

Step 1 - grab credentials once (asks for the PIN mailed to you):

    python examples/watch_favorites.py --login --email you@example.com

Step 2 - watch, notify, and optionally reserve one bag automatically:

    python examples/watch_favorites.py --notify https://ntfy.sh/your-private-topic --reserve 1

Notifications go to ntfy, Bark (api.day.app) or Telegram; without any of those
flags everything is just logged to stdout.

Credentials are stored in ~/.config/tgtg/credentials.json (mode 0600), not in the
repository. Override with --credentials or $TGTG_CREDENTIALS.

Restraint is what keeps this working. The defaults poll every two minutes inside
an active window, keep one stable device identity across restarts, refuse to run
twice at once, cap how much they ask for in a day, and give up entirely once
DataDome starts challenging instead of retrying into a deeper hole.
"""

import argparse
import base64
import fcntl
import json
import os
import random
import re
import shutil
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tgtg import API_ITEM_ENDPOINT, TgtgClient  # noqa: E402
from tgtg.exceptions import TgtgAPIError  # noqa: E402

# Credentials live outside the repository so an editor, a stray commit or a shared
# folder cannot pick them up.
CONFIG_DIR = Path.home() / ".config" / "tgtg"
DEFAULT_CREDENTIALS = CONFIG_DIR / "credentials.json"
DEFAULT_STATE = CONFIG_DIR / "state.json"
DEFAULT_LOCK = CONFIG_DIR / "watcher.lock"
LEGACY_CREDENTIALS = Path("tgtg_credentials.json")
CREDENTIALS_MODE = 0o600
CREDENTIALS_DIR_MODE = 0o700
# Deliberately loose: over-redacting a log line costs nothing, leaking a token costs a lot.
JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]{2,}\.[A-Za-z0-9_-]+\.?[A-Za-z0-9_-]*")
OPAQUE_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_~-]{40,}")

DEFAULT_INTERVAL = 120
DEFAULT_JITTER = 30
DEFAULT_ACTIVE_HOURS = "7-23"
DEFAULT_MAX_POLLS_PER_DAY = 600
DEFAULT_MAX_RESERVES_PER_DAY = 3
BLOCK_BACKOFF_BASE = 300
BLOCK_BACKOFF_CAP = 4 * 3600
MAX_CONSECUTIVE_BLOCKS = 5
RATE_LIMIT_BACKOFF = 900
ERROR_BACKOFF_CAP = 600
MIN_SLEEP = 5
# token/v1/refresh is the most heavily protected endpoint, so only go there when the
# access token is genuinely about to die rather than on a fixed four hour timer.
TOKEN_REFRESH_MARGIN = 600


def log(message):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}", flush=True)


def redact(text):
    """Strip anything token-shaped before it can reach a log line or a terminal scrollback."""
    text = JWT_PATTERN.sub("<jwt redacted>", str(text))
    return OPAQUE_TOKEN_PATTERN.sub("<redacted>", text)


def access_token_expiry(access_token):
    """Read 'exp' out of the JWT - unverified, it is our own token - to learn when it really dies."""
    try:
        claims = access_token.split(".")[1]
        claims += "=" * (-len(claims) % 4)
        return datetime.fromtimestamp(json.loads(base64.urlsafe_b64decode(claims))["exp"])
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return None


def _write_private_json(path, payload):
    """Atomic write that is never briefly world-readable and cannot leave a truncated file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent == CONFIG_DIR:
        path.parent.chmod(CREDENTIALS_DIR_MODE)
    tmp = path.with_name(path.name + ".tmp")
    descriptor = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, CREDENTIALS_MODE)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(tmp, path)


def load_credentials(path):
    if not path.exists():
        return None
    mode = path.stat().st_mode & 0o777
    if mode & 0o077:
        log(f"WARNING: {path} was readable by other accounts (mode {mode:04o}), tightening it")
        path.chmod(CREDENTIALS_MODE)
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def save_credentials(path, credentials):
    _write_private_json(path, credentials)


def resolve_credentials_path(explicit):
    """--credentials wins, then $TGTG_CREDENTIALS, then ~/.config/tgtg/credentials.json."""
    if explicit is not None:
        return explicit.expanduser()
    from_env = os.environ.get("TGTG_CREDENTIALS")
    return Path(from_env).expanduser() if from_env else DEFAULT_CREDENTIALS


def migrate_legacy_credentials(target):
    """Move a credential file left inside the repository out to the config directory."""
    if target.exists() or not LEGACY_CREDENTIALS.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.parent.chmod(CREDENTIALS_DIR_MODE)
    shutil.move(str(LEGACY_CREDENTIALS), str(target))
    target.chmod(CREDENTIALS_MODE)
    log(f"Moved {LEGACY_CREDENTIALS} out of the repository to {target}")


def load_state(path):
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def save_state(path, state):
    _write_private_json(path, state)


def acquire_lock(path):
    """Take an exclusive lock so two watchers can never poll the same account at once."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("w")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def parse_active_hours(value):
    """'7-23' -> (7, 23). '0-24' (or None) means no restriction."""
    if not value:
        return None
    start, separator, end = value.partition("-")
    if not separator:
        raise ValueError("active hours must look like 7-23")
    start, end = int(start), int(end)
    if not (0 <= start <= 24 and 0 <= end <= 24):
        raise ValueError("active hours must be between 0 and 24")
    if start == end or (start == 0 and end == 24):
        return None
    return start, end


def seconds_until_active(window, now):
    """0 while inside the window, otherwise how long to wait for it to open."""
    if window is None:
        return 0
    start, end = window
    hour = now.hour + now.minute / 60
    inside = start <= hour < end if start < end else (hour >= start or hour < end)
    if inside:
        return 0
    target = now.replace(hour=start % 24, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def seconds_until_midnight(now):
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return (tomorrow - now).total_seconds()


class Notifier:
    """Fan a message out to ntfy / Bark / Telegram. Every backend is optional."""

    def __init__(self, webhook_url=None, telegram_token=None, telegram_chat=None):
        self.webhook_url = webhook_url
        self.telegram_token = telegram_token
        self.telegram_chat = telegram_chat

    def send(self, title, message):
        log(f"{title} | {message}")
        body = f"{title}\n{message}"
        if self.webhook_url:
            self._deliver("webhook", self._send_webhook, body, title, message)
        if self.telegram_token and self.telegram_chat:
            self._deliver("telegram", self._send_telegram, body)

    @staticmethod
    def _deliver(name, sender, *args):
        try:
            sender(*args)
        except requests.RequestException as exc:
            log(f"Notification via {name} failed: {redact(exc)}")

    def _send_webhook(self, body, title, message):
        if "api.day.app" in self.webhook_url:
            requests.post(self.webhook_url, json={"title": title, "body": message}, timeout=10)
        else:
            requests.post(self.webhook_url, data=body.encode("utf-8"), timeout=10)

    def _send_telegram(self, body):
        requests.post(
            f"https://api.telegram.org/bot{self.telegram_token}/sendMessage",
            json={"chat_id": self.telegram_chat, "text": body},
            timeout=10,
        )


def format_price(price):
    if not price:
        return ""
    decimals = price.get("decimals", 2)
    amount = price.get("minor_units", 0) / (10**decimals)
    return f"{amount:.2f} {price.get('code', '')}".strip()


def format_pickup(interval):
    if not interval:
        return ""
    try:
        start = datetime.fromisoformat(interval["start"].replace("Z", "+00:00")).astimezone()
        end = datetime.fromisoformat(interval["end"].replace("Z", "+00:00")).astimezone()
    except (AttributeError, KeyError, ValueError):
        return ""
    return f"{start:%m-%d %H:%M}-{end:%H:%M}"


def item_name(item):
    return item.get("display_name") or item.get("store", {}).get("store_name") or "?"


def describe(item):
    parts = [f"{item.get('items_available', 0)} left"]
    price = format_price(item.get("item", {}).get("price_including_taxes"))
    if price:
        parts.append(price)
    pickup = format_pickup(item.get("pickup_interval"))
    if pickup:
        parts.append(f"pickup {pickup}")
    return ", ".join(parts)


def matches_filter(item, wanted):
    if not wanted:
        return True
    haystack = f"{item_name(item)} {item.get('store', {}).get('store_name', '')}".lower()
    return any(needle in haystack for needle in wanted)


def is_captcha_block(payload):
    return "captcha-delivery" in payload or "interstitial" in payload


def explain_api_error(exc):
    """Turn a TgtgAPIError into one readable, redacted sentence."""
    status = exc.args[0] if exc.args else None
    payload = redact(exc.args[1])[:200] if len(exc.args) > 1 else ""
    if status == 403 and is_captcha_block(payload):
        return (
            "DataDome is serving a captcha challenge, so this IP/client is still flagged. "
            "Nothing here can solve it - wait a few hours, or try from a different network."
        )
    if status == 403:
        return f"403 - credentials rejected, re-run with --login. Response: {payload}"
    if status == 429:
        return "429 - rate limited, polling too fast."
    return f"API error {redact(exc)}"


def diagnose(args):
    """One unauthenticated probe with a brand new identity: does this network get through?"""
    client = TgtgClient(timeout=30)
    url = client._get_url(API_ITEM_ENDPOINT)
    probe = {"origin": {"latitude": 0.0, "longitude": 0.0}, "radius": 1, "page_size": 1}
    try:
        response = client._post(url, json=probe)
    except requests.RequestException as exc:
        log(f"Network error: {redact(exc)}")
        return 2

    body = redact(response.content.decode("utf-8", "replace"))[:200]
    if is_captcha_block(body):
        log("BLOCKED - DataDome challenges even a brand new client here, so the flag is on this network.")
        log("Try a different one (phone hotspot). Your account may well be fine.")
        return 2
    if response.status_code in (401, 403):
        log("NETWORK OK - a fresh client got through; it was refused only for having no token.")
        log("If --list still fails from here, the flag follows your stored identity: try --reset-identity.")
        return 0
    log(f"Unexpected status {response.status_code}: {body}")
    return 1


def reset_identity(args):
    """Forget the stored device fingerprint so the next run looks like a fresh install."""
    state = load_state(args.state)
    for key in ("user_agent", "correlation_id"):
        state.pop(key, None)
    save_state(args.state, state)

    credentials = load_credentials(args.credentials)
    if credentials:
        client = TgtgClient(**credentials, user_agent="reset")
        client._drop_stored_datadome()
        credentials["cookie"] = client.cookie
        save_credentials(args.credentials, credentials)
    log("Device identity cleared - the next run picks a new user agent, correlation id and cookie.")
    return 0


class Watcher:
    """Polls favourites under a request budget, one identity, and a hard stop when blocked."""

    def __init__(self, args, notifier):
        self.args = args
        self.notifier = notifier
        self.credentials = load_credentials(args.credentials)
        self.state = load_state(args.state)
        self.seen = {}
        self.reserved = set()
        self.failures = 0
        self.blocks = 0
        self.first_run = True
        self.stopping = False
        self.client = self._build_client()

    # -- identity -------------------------------------------------------

    def _token_freshness(self):
        """When the stored access token is still good, tell the client so it skips the refresh."""
        expiry = access_token_expiry(self.credentials.get("access_token"))
        if expiry:
            remaining = int((expiry - datetime.now()).total_seconds() - TOKEN_REFRESH_MARGIN)
            return (datetime.now(), remaining) if remaining > 0 else (None, None)
        if self.state.get("last_token_refresh"):
            try:
                return datetime.fromisoformat(self.state["last_token_refresh"]), None
            except ValueError:
                pass
        return None, None

    def _build_client(self):
        """Reuse one device identity across restarts instead of minting a new one each launch."""
        last_refresh, lifetime = self._token_freshness()
        extra = {"access_token_lifetime": lifetime} if lifetime is not None else {}
        if lifetime is not None:
            log(f"Access token still valid for {lifetime / 3600:.1f}h, skipping the token refresh")
        client = TgtgClient(
            **self.credentials,
            user_agent=self.state.get("user_agent"),
            correlation_id=self.state.get("correlation_id"),
            last_time_token_refreshed=last_refresh,
            timeout=30,
            **extra,
        )
        self.state["user_agent"] = client.user_agent
        self.state["correlation_id"] = client.correlation_id
        return client

    def persist(self):
        current = {
            "access_token": self.client.access_token,
            "refresh_token": self.client.refresh_token,
            "cookie": self.client.cookie,
        }
        if all(current.values()) and current != self.credentials:
            self.credentials = current
            save_credentials(self.args.credentials, current)
            log("Refreshed tokens saved")
        if self.client.last_time_token_refreshed:
            self.state["last_token_refresh"] = self.client.last_time_token_refreshed.isoformat()
        save_state(self.args.state, self.state)

    # -- budget ---------------------------------------------------------

    def _roll_day(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self.state.get("day") != today:
            self.state.update(day=today, polls=0, reserves=0)

    def _budget_left(self):
        self._roll_day()
        return self.args.max_polls_per_day - self.state.get("polls", 0)

    def _count_poll(self):
        self.state["polls"] = self.state.get("polls", 0) + 1

    # -- polling --------------------------------------------------------

    def poll_once(self):
        items = [item for item in self.client.get_favorites() if matches_filter(item, self.args.store)]
        self._count_poll()

        for item in items:
            item_id = item["item"]["item_id"]
            available = item.get("items_available", 0)
            previous = self.seen.get(item_id, 0)
            self.seen[item_id] = available

            if available == 0:
                self.reserved.discard(item_id)
                continue
            if self.first_run:
                log(f"Already available at startup: {item_name(item)} ({describe(item)})")
                continue
            if previous > 0:
                continue

            self.notifier.send("Surprise bag available", f"{item_name(item)} - {describe(item)}")
            if self.args.reserve and item_id not in self.reserved and self.try_reserve(item):
                self.reserved.add(item_id)

        if self.first_run:
            window = self.args.active_hours or "always"
            log(f"Watching {len(items)} favourite(s) | every ~{self.args.interval}s | window {window}")
            self.first_run = False

    def list_favourites(self):
        """Print every favourite with its availability, so --store filters can be written."""
        items = self.client.get_favorites()
        self._count_poll()
        if not items:
            log("No favourites yet - add some in the phone app first.")
            return
        log(f"{len(items)} favourite(s):")
        for item in items:
            marker = "AVAILABLE" if item.get("items_available", 0) > 0 else "  -      "
            print(f"  {marker}  {item_name(item)} - {describe(item)}")

    def try_reserve(self, item):
        self._roll_day()
        if self.state.get("reserves", 0) >= self.args.max_reserves_per_day:
            log("Daily reservation cap reached, not reserving (notification still sent)")
            return False
        wanted = min(self.args.reserve, item.get("items_available", 0))
        if wanted < 1:
            return False
        try:
            order = self.client.create_order(item["item"]["item_id"], wanted)
        except TgtgAPIError as exc:
            self.notifier.send("Reservation failed", f"{item_name(item)}: {redact(exc)}")
            return False
        self.state["reserves"] = self.state.get("reserves", 0) + 1
        order_id = order.get("id") or order.get("order_id") or "?"
        self.notifier.send(
            "RESERVED - pay in the app now",
            f"{item_name(item)} x{wanted} (order {order_id}). The reservation expires in a few minutes.",
        )
        return True

    # -- failure handling ------------------------------------------------

    def handle_api_error(self, exc):
        """Return how long to wait, or None to stop the watcher for good."""
        status = exc.args[0] if exc.args else None
        payload = redact(exc.args[1])[:200] if len(exc.args) > 1 else ""

        if status == 403 and is_captcha_block(payload):
            self.blocks += 1
            if self.blocks >= MAX_CONSECUTIVE_BLOCKS:
                self.notifier.send(
                    "Watcher stopped",
                    f"DataDome challenged {self.blocks} times in a row. Retrying only digs deeper - "
                    "leave this IP alone for a few hours before starting again.",
                )
                return None
            delay = min(BLOCK_BACKOFF_CAP, BLOCK_BACKOFF_BASE * 2 ** (self.blocks - 1))
            log(f"{explain_api_error(exc)} ({self.blocks}/{MAX_CONSECUTIVE_BLOCKS}) Waiting {delay:.0f}s.")
            return delay

        self.failures += 1
        if status == 403:
            log(f"{explain_api_error(exc)} Waiting {BLOCK_BACKOFF_BASE}s.")
            return BLOCK_BACKOFF_BASE
        if status == 429:
            log(f"{explain_api_error(exc)} Waiting {RATE_LIMIT_BACKOFF}s.")
            return RATE_LIMIT_BACKOFF
        delay = min(ERROR_BACKOFF_CAP, self.args.interval * 2**self.failures)
        log(f"{explain_api_error(exc)} Retrying in {delay:.0f}s.")
        return delay

    # -- main loop -------------------------------------------------------

    def next_delay(self):
        return max(MIN_SLEEP, self.args.interval + random.uniform(-self.args.jitter, self.args.jitter))

    def sleep(self, seconds):
        """Interruptible sleep so a signal does not have to wait out a four hour backoff."""
        deadline = time.monotonic() + seconds
        while not self.stopping:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(remaining, 1.0))

    def run(self):
        while not self.stopping:
            waiting = seconds_until_active(self.args.active_hours_window, datetime.now())
            if waiting:
                log(f"Outside the active window, sleeping {waiting / 3600:.1f}h")
                self.sleep(waiting)
                continue

            if self._budget_left() <= 0:
                waiting = seconds_until_midnight(datetime.now())
                log(f"Daily poll budget spent, sleeping {waiting / 3600:.1f}h")
                self.sleep(waiting)
                continue

            try:
                self.poll_once()
            except TgtgAPIError as exc:
                delay = self.handle_api_error(exc)
                self.persist()
                if delay is None:
                    return 2
                self.sleep(delay)
                continue
            except requests.RequestException as exc:
                self.failures += 1
                delay = min(ERROR_BACKOFF_CAP, self.args.interval * 2**self.failures)
                log(f"Network error {redact(exc)} - retrying in {delay:.0f}s.")
                self.sleep(delay)
                continue

            self.failures = 0
            self.blocks = 0
            self.persist()
            if self.args.once:
                return 0
            self.sleep(self.next_delay())
        return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Watch TooGoodToGo favourites for available surprise bags.")
    parser.add_argument("--login", action="store_true", help="run the interactive PIN login and store credentials")
    parser.add_argument("--email", default=os.environ.get("TGTG_EMAIL"), help="account email, only used with --login")
    parser.add_argument(
        "--credentials",
        type=Path,
        default=None,
        help=f"credentials JSON file (default: $TGTG_CREDENTIALS or {DEFAULT_CREDENTIALS})",
    )
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE, help="device identity and daily counters")
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK, help="single instance lock file")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="seconds between polls")
    parser.add_argument("--jitter", type=float, default=DEFAULT_JITTER, help="random +/- seconds added to interval")
    parser.add_argument(
        "--active-hours",
        default=DEFAULT_ACTIVE_HOURS,
        help="only poll inside this local-time window, e.g. 7-23; use 0-24 to never sleep",
    )
    parser.add_argument(
        "--max-polls-per-day", type=int, default=DEFAULT_MAX_POLLS_PER_DAY, help="hard ceiling on polls per day"
    )
    parser.add_argument(
        "--max-reserves-per-day", type=int, default=DEFAULT_MAX_RESERVES_PER_DAY, help="cap on automatic reservations"
    )
    parser.add_argument("--reserve", type=int, default=0, help="reserve up to N bags automatically (0 disables)")
    parser.add_argument("--store", action="append", default=[], help="only watch stores matching this text")
    parser.add_argument("--once", action="store_true", help="poll a single time and exit")
    parser.add_argument("--list", action="store_true", help="print your favourites and exit")
    parser.add_argument("--diagnose", action="store_true", help="one anonymous probe: is this network blocked?")
    parser.add_argument("--reset-identity", action="store_true", help="forget the stored device fingerprint")
    parser.add_argument("--notify", default=os.environ.get("TGTG_NOTIFY_URL"), help="ntfy or Bark webhook URL")
    parser.add_argument("--telegram-token", default=os.environ.get("TGTG_TELEGRAM_TOKEN"), help="Telegram bot token")
    parser.add_argument("--telegram-chat", default=os.environ.get("TGTG_TELEGRAM_CHAT"), help="Telegram chat id")
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.store = [needle.lower() for needle in args.store]
    args.credentials = resolve_credentials_path(args.credentials)
    migrate_legacy_credentials(args.credentials)
    try:
        args.active_hours_window = parse_active_hours(args.active_hours)
    except ValueError as exc:
        parser.error(str(exc))

    if args.login:
        if not args.email:
            parser.error("--login needs --email (or the TGTG_EMAIL environment variable)")
        try:
            save_credentials(args.credentials, TgtgClient(email=args.email).get_credentials())
        except TgtgAPIError as exc:
            log(explain_api_error(exc))
            return 2
        log(f"Credentials saved to {args.credentials}. Run again without --login to start watching.")
        return 0

    if args.diagnose:
        return diagnose(args)

    if args.reset_identity:
        return reset_identity(args)

    if not load_credentials(args.credentials):
        log(f"No credentials at {args.credentials}. Run with --login --email you@example.com first.")
        return 1

    if args.list:
        watcher = Watcher(args, Notifier())
        try:
            watcher.list_favourites()
        except TgtgAPIError as exc:
            log(explain_api_error(exc))
            return 2
        finally:
            watcher.persist()
        return 0

    lock = acquire_lock(args.lock)
    if lock is None:
        log(f"Another watcher already holds {args.lock}. Refusing to poll the same account twice.")
        return 1

    watcher = Watcher(args, Notifier(args.notify, args.telegram_token, args.telegram_chat))

    def stop(_signum, _frame):
        log("Shutting down, saving state...")
        watcher.stopping = True

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    if not args.once:
        # Do not start on a suspiciously round schedule after a restart.
        watcher.sleep(random.uniform(0, args.jitter))

    try:
        return watcher.run()
    finally:
        watcher.persist()
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    sys.exit(main())
