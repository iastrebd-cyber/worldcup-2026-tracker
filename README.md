# ⚽ World Cup 2026 Tracker

Automated tracker for the **FIFA World Cup 2026** built on
[football-data.org](https://www.football-data.org/) and the Google Calendar API,
driven entirely by GitHub Actions.

## What it does

| Script | Purpose | Schedule |
| --- | --- | --- |
| `standings.py` | Renders all 12 group tables to [`standings.md`](standings.md) and, once the group stage is over, the knockout tree to [`bracket.md`](bracket.md). Commits the result back to the repo. | every 3 h |
| `notify.py` | Creates **one** consolidated event ("⚽ ЧМ-2026: матчи") for the next 24 h of matches in the main calendar. Times in `America/New_York`. Deletes the previous summary first. | 13:00 & 01:00 UTC |
| `match_events.py` | Creates **one event per match** for the next 7 days in the dedicated WC calendar — 2 h long, popup reminder 10 min before. Idempotent on `match_id`: skips unchanged, updates moved, deletes cancelled. | every 6 h |

All jobs can also be run manually via **workflow_dispatch** (input `job`: `all`, `standings`, `notify`, `match_events`).

## Configuration (GitHub Actions secrets)

| Secret | Meaning |
| --- | --- |
| `FOOTBALL_DATA_API_KEY` | football-data.org API token |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON of the `wc-notifier` service-account key |
| `GOOGLE_CALENDAR_ID` | Main calendar (e.g. `you@gmail.com`) for the daily summary |
| `WC_CALENDAR_ID` | Dedicated WC calendar id for per-match events |

> Both calendars must be **shared with the service-account email** with
> _"Make changes to events"_ permission, otherwise the calendar calls return 403/404.

## Local run

```powershell
python -m pip install -r requirements.txt
$env:FOOTBALL_DATA_API_KEY="..."
python standings.py            # writes standings.md / bracket.md
# Calendar scripts also need GOOGLE_SERVICE_ACCOUNT_JSON (or sa-key.json) + calendar ids
python notify.py
python match_events.py
```

API usage stays under the free-tier limit of 10 requests/minute, with automatic
retries on HTTP 429.
