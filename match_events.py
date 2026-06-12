"""Create / update / delete one calendar event per World Cup 2026 match in the
next 48 hours, in the dedicated WC calendar (WC_CALENDAR_ID).

Idempotency is keyed on the match id stored in extendedProperties.private:
  * event missing            -> create it
  * event exists, same time  -> skip
  * event exists, time moved  -> update it
  * match cancelled/postponed -> delete the event
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import wc_api
from flags import flag
from gcal import calendar_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wc")

WINDOW_HOURS = 48
MATCH_DURATION_HOURS = 2
TZ = "America/New_York"

P_MANAGED = "wc2026_managed"
P_MATCH_ID = "wc2026_match_id"
P_START = "wc2026_start"

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


def _title(m: dict) -> str:
    home = m.get("homeTeam", {}).get("name") or "TBD"
    away = m.get("awayTeam", {}).get("name") or "TBD"
    return f"⚽ {home} — {away}"


def _description(m: dict) -> str:
    stage = STAGE_RU.get(m.get("stage", ""), m.get("stage", ""))
    grp = (m.get("group") or "").replace("GROUP_", "Группа ")
    venue = m.get("venue") or "уточняется"
    home = m.get("homeTeam", {}).get("name") or "TBD"
    away = m.get("awayTeam", {}).get("name") or "TBD"
    parts = [
        f"{flag(home)} {home} — {away} {flag(away)}",
        "",
        f"Стадия: {stage}",
    ]
    if grp:
        parts.append(f"Группа: {grp}")
    if m.get("matchday"):
        parts.append(f"Тур: {m['matchday']}")
    parts.append(f"Стадион: {venue}")
    return "\n".join(parts)


def _body(m: dict) -> dict:
    start = _parse(m["utcDate"])
    end = start + timedelta(hours=MATCH_DURATION_HOURS)
    return {
        "summary": _title(m),
        "description": _description(m),
        "start": {"dateTime": start.isoformat().replace("+00:00", "Z"), "timeZone": TZ},
        "end": {"dateTime": end.isoformat().replace("+00:00", "Z"), "timeZone": TZ},
        "extendedProperties": {
            "private": {
                P_MANAGED: "1",
                P_MATCH_ID: str(m["id"]),
                P_START: m["utcDate"],
            }
        },
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}]},
    }


def load_managed_events(service, calendar_id: str) -> dict[str, dict]:
    events: dict[str, dict] = {}
    page_token = None
    while True:
        resp = service.events().list(
            calendarId=calendar_id,
            privateExtendedProperty=f"{P_MANAGED}=1",
            showDeleted=False,
            singleEvents=True,
            maxResults=2500,
            pageToken=page_token,
        ).execute()
        for ev in resp.get("items", []):
            mid = ev.get("extendedProperties", {}).get("private", {}).get(P_MATCH_ID)
            if mid:
                events[mid] = ev
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return events


def main() -> None:
    calendar_id = os.environ.get("WC_CALENDAR_ID")
    if not calendar_id:
        raise SystemExit("WC_CALENDAR_ID is not set.")

    service = calendar_service()
    existing = load_managed_events(service, calendar_id)
    log.info("Found %d managed events already in calendar", len(existing))

    all_matches = wc_api.matches().get("matches", [])
    by_id = {str(m["id"]): m for m in all_matches}

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=WINDOW_HOURS)

    created = updated = skipped = deleted = 0

    # 1) Upsert matches inside the 48h window.
    for m in all_matches:
        if not m.get("utcDate"):
            continue
        when = _parse(m["utcDate"])
        if not (now <= when <= horizon):
            continue
        mid = str(m["id"])
        status = m.get("status")

        if status in {"CANCELLED", "POSTPONED"}:
            if mid in existing:
                service.events().delete(calendarId=calendar_id, eventId=existing[mid]["id"]).execute()
                deleted += 1
                log.info("Deleted event for %s match %s", status, mid)
            continue

        body = _body(m)
        if mid in existing:
            ev = existing[mid]
            stored_start = ev.get("extendedProperties", {}).get("private", {}).get(P_START)
            if stored_start == m["utcDate"]:
                skipped += 1
                continue
            service.events().update(calendarId=calendar_id, eventId=ev["id"], body=body).execute()
            updated += 1
            log.info("Updated event for match %s (time changed %s -> %s)", mid, stored_start, m["utcDate"])
        else:
            service.events().insert(calendarId=calendar_id, body=body).execute()
            created += 1
            log.info("Created event for match %s at %s", mid, m["utcDate"])

    # 2) Delete events whose match was cancelled/postponed (even outside the window).
    for mid, ev in existing.items():
        match = by_id.get(mid)
        if match and match.get("status") in {"CANCELLED", "POSTPONED"}:
            try:
                service.events().delete(calendarId=calendar_id, eventId=ev["id"]).execute()
                deleted += 1
                log.info("Deleted event for cancelled match %s", mid)
            except Exception as exc:  # already gone
                log.warning("Could not delete %s: %s", mid, exc)

    log.info("Done. created=%d updated=%d skipped=%d deleted=%d", created, updated, skipped, deleted)


if __name__ == "__main__":
    main()
