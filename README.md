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

## 🌐 Standings web page (GitHub Pages)

A standalone, **script-free** HTML page (works inside the Telegram in-app
browser, which does not run JavaScript) showing the live group tables and a
knockout-bracket placeholder. All rendering happens at build time in Python.

| File | Purpose |
| --- | --- |
| `template.html` | Layout + CSS only, no `<script>`. Tabs are pure CSS (hidden `radio` + `label`). Has two markers: `<!-- GROUPS -->` and `<!-- UPDATED -->`. |
| `build_table.py` | Fills the template and writes `docs/index.html`. Live mode pulls `/v4/competitions/WC/standings` and `/matches`; `--mock` uses `mock_data.py` for offline builds. |
| `mock_data.py` | Offline group-stage snapshot (18 June 2026). |
| `.github/workflows/build-table.yml` | Builds and deploys the page to Pages — every 2 h, on manual dispatch, and on push to `main` touching `build_table.py` / `template.html` / the workflow. |

### Setup

1. **Files** — drop `template.html`, `build_table.py`, `mock_data.py` in the repo
   root and the workflow under `.github/workflows/`.
2. **Secret** — set the Actions secret **`FOOTBALL_DATA_API_KEY`** to a freshly
   **re-issued** football-data.org token.
3. **Pages** — in **Settings → Pages**, set **Source = GitHub Actions**.
4. **First run** — trigger it once via **Actions → Build standings page →
   Run workflow** (the schedule takes over afterwards).

### Local build

```powershell
python build_table.py --mock     # offline, writes docs/index.html
$env:FOOTBALL_DATA_API_KEY="..."
python build_table.py            # live data
```
