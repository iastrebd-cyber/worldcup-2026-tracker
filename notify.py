"""Create a single consolidated calendar event summarising every World Cup 2026
match in the next 24 hours, in the main calendar (GOOGLE_CALENDAR_ID).

The previous day's summary is deleted before the new one is created, so the
calendar never accumulates stale summaries.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import wc_api
from flags import flag
from gcal import calendar_service
from venues import venue_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wc")

TZ = ZoneInfo("America/New_York")
SUMMARY_TAG_KEY = "wc2026_summary"
SUMMARY_TAG_VALUE = "daily"
WINDOW_HOURS = 24
EVENT_TITLE = "⚽ ЧМ-2026: матчи"

STAGE_RU = {
    "GROUP_STAGE": "Групповой этап",
    "LAST_32": "1/16 финала",
    "LAST_16": "1/8 финала",
    "QUARTER_FINALS": "1/4 финала",
    "SEMI_FINALS": "1/2 финала",
    "THIRD_PLACE": "Матч за 3-е место",
    "FINAL": "Финал",
}


def _parse(utc: str) -> datetime:
    return datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone(timezone.utc)


def upcoming_matches() -> list[dict]:
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=WINDOW_HOURS)
    out = []
    for m in wc_api.matches().get("matches", []):
        if m.get("status") in {"CANCELLED", "POSTPONED", "FINISHED"}:
            continue
        if not m.get("utcDate"):
            continue
        when = _parse(m["utcDate"])
        if now <= when <= horizon:
            out.append(m)
    out.sort(key=lambda m: m["utcDate"])
    return out


def build_description(matches: list[dict]) -> str:
    lines = ["Матчи ЧМ-2026 на ближайшие 24 часа (время — America/New_York):", ""]
    for m in matches:
        local = _parse(m["utcDate"]).astimezone(TZ)
        home = m.get("homeTeam", {}).get("name") or "TBD"
        away = m.get("awayTeam", {}).get("name") or "TBD"
        stage = STAGE_RU.get(m.get("stage", ""), m.get("stage", ""))
        grp = (m.get("group") or "").replace("GROUP_", "Группа ")
        tag = f"{stage}, {grp}" if grp else stage
        city = venue_for(m, with_stadium=False)
        loc = f" · {city}" if city else ""
        lines.append(
            f"• {local:%H:%M} — {flag(home)} {home} — {away} {flag(away)}  ({tag}){loc}"
        )
    return "\n".join(lines)


def delete_old_summaries(service, calendar_id: str) -> None:
    resp = service.events().list(
        calendarId=calendar_id,
        privateExtendedProperty=f"{SUMMARY_TAG_KEY}={SUMMARY_TAG_VALUE}",
        showDeleted=False,
        maxResults=2500,
        singleEvents=True,
    ).execute()
    for ev in resp.get("items", []):
        service.events().delete(calendarId=calendar_id, eventId=ev["id"]).execute()
        log.info("Deleted previous summary %s", ev["id"])


def main() -> None:
    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID", "iastrebd@gmail.com")
    service = calendar_service()

    log.info("Removing stale summaries from %s", calendar_id)
    delete_old_summaries(service, calendar_id)

    matches = upcoming_matches()
    if not matches:
        log.info("No matches in the next %d hours; nothing to create.", WINDOW_HOURS)
        return

    first = _parse(matches[0]["utcDate"]).astimezone(TZ)
    last = _parse(matches[-1]["utcDate"]).astimezone(TZ) + timedelta(hours=2)

    body = {
        "summary": EVENT_TITLE,
        "description": build_description(matches),
        "start": {"dateTime": first.isoformat(), "timeZone": "America/New_York"},
        "end": {"dateTime": last.isoformat(), "timeZone": "America/New_York"},
        "extendedProperties": {"private": {SUMMARY_TAG_KEY: SUMMARY_TAG_VALUE}},
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 30}]},
    }
    created = service.events().insert(calendarId=calendar_id, body=body).execute()
    log.info("Created summary event with %d matches: %s", len(matches), created.get("htmlLink"))


if __name__ == "__main__":
    main()
