"""Shared football-data.org API client for the World Cup 2026 tracker.

Handles authentication, a conservative client-side rate limit (the free tier
allows 10 requests/minute) and automatic retries on HTTP 429.
"""
from __future__ import annotations

import logging
import os
import time
from collections import deque
from typing import Any

import requests

log = logging.getLogger("wc")

BASE_URL = "https://api.football-data.org/v4"
COMPETITION = "2000"  # FIFA World Cup (code "WC")

# Free tier: 10 requests / minute. Stay just under it.
_MAX_PER_WINDOW = 9
_WINDOW_SECONDS = 60.0
_call_times: deque[float] = deque()


def _api_key() -> str:
    key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not key:
        raise SystemExit("FOOTBALL_DATA_API_KEY is not set in the environment.")
    return key


def _throttle() -> None:
    """Block until making another request keeps us under the rate limit."""
    now = time.monotonic()
    while _call_times and now - _call_times[0] >= _WINDOW_SECONDS:
        _call_times.popleft()
    if len(_call_times) >= _MAX_PER_WINDOW:
        sleep_for = _WINDOW_SECONDS - (now - _call_times[0]) + 0.1
        if sleep_for > 0:
            log.info("Rate limit guard: sleeping %.1fs", sleep_for)
            time.sleep(sleep_for)
    _call_times.append(time.monotonic())


def get(path: str, *, max_retries: int = 5) -> dict[str, Any]:
    """GET a JSON endpoint with rate limiting and 429 retries."""
    url = f"{BASE_URL}/{path.lstrip('/')}"
    headers = {"X-Auth-Token": _api_key()}
    attempt = 0
    while True:
        attempt += 1
        _throttle()
        log.info("GET %s (attempt %d)", url, attempt)
        try:
            resp = requests.get(url, headers=headers, timeout=30)
        except requests.RequestException as exc:
            if attempt > max_retries:
                raise
            wait = min(2 ** attempt, 60)
            log.warning("Network error %s; retrying in %ss", exc, wait)
            time.sleep(wait)
            continue

        if resp.status_code == 429:
            if attempt > max_retries:
                resp.raise_for_status()
            retry_after = resp.headers.get("Retry-After")
            wait = int(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 60)
            log.warning("HTTP 429 rate limited; retrying in %ss", wait)
            time.sleep(wait)
            continue

        if resp.status_code >= 500:
            if attempt > max_retries:
                resp.raise_for_status()
            wait = min(2 ** attempt, 60)
            log.warning("HTTP %s server error; retrying in %ss", resp.status_code, wait)
            time.sleep(wait)
            continue

        resp.raise_for_status()
        return resp.json()


def standings() -> dict[str, Any]:
    return get(f"competitions/{COMPETITION}/standings")


def matches() -> dict[str, Any]:
    return get(f"competitions/{COMPETITION}/matches")


def match(match_id: str | int) -> dict[str, Any]:
    """Fetch a single match by id.

    Used for matches that have dropped out of the bulk `matches()` list (the
    competition feed stops returning older finished matches) so the final score
    can still be rendered onto an existing managed event.
    """
    resp = get(f"matches/{match_id}")
    # v4 returns the match object at the top level; tolerate a `match` wrapper.
    return resp.get("match", resp)
