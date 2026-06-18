"""Create / update / delete one calendar event per World Cup 2026 match in the
next 7 days, in the dedicated WC calendar (WC_CALENDAR_ID).

Idempotency is keyed on the match id stored in extendedProperties.private:
  * event missing             -> create it
  * event exists, same sig    -> skip
  * event exists, sig changed -> update it (time moved, or final score arrived)
  * match cancelled/postponed -> delete the event

A managed event is kept fresh even after kickoff falls out of the forward
window: the upsert loop runs over the union of the API match list and the ids
we already have events for, fetching a single match on demand when the bulk
feed has dropped it, so the final score lands on it once the match is FINISHED.
"""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone

import wc_api
from flags import flag
from gcal import calendar_service
from venues import venue_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wc")

WINDOW_HOURS = 168  # 7 days
MATCH_DURATION_HOURS = 2
TZ = "America/New_York"

P_MANAGED = "wc2026_managed"
P_MATCH_ID = "wc2026_match_id"
P_START = "wc2026_start"
P_SIG = "wc2026_sig"
P_FINAL = "wc2026_final"  # "1" once the final score has been rendered onto the event

STAGE_RU = {
    "GROUP_STAGE": "Групповой этап",
    "LAST_32": "1/16 финала",
    "LAST_16": "1/8 финала",
    "QUARTER_FINALS": "1/4 финала",
    "SEMI_FINALS": "1/2 финала",
    "THIRD_PLACE": "Матч за 3-е место",
    "FINAL": "Финал",
}

DURATION_RU = {
    "EXTRA_TIME": "в доп. время",
    "PENALTY_SHOOTOUT": "по пенальти",
}


def _parse(utc: str) -> datetime:
    return datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone(timezone.utc)


def _final_score(m: dict) -> str | None:
    """`"2:1"` once the match is over, else None (no score to show yet)."""
    if m.get("status") != "FINISHED":
        return None
    ft = (m.get("score") or {}).get("fullTime") or {}
    home, away = ft.get("home"), ft.get("away")
    if home is None or away is None:
        return None
    return f"{home}:{away}"


def _duration_note(m: dict) -> str | None:
    return DURATION_RU.get((m.get("score") or {}).get("duration", ""))


def _title(m: dict) -> str:
    home = m.get("homeTeam", {}).get("name") or "TBD"
    away = m.get("awayTeam", {}).get("name") or "TBD"
    score = _final_score(m)
    if score:
        return f"⚽ {home} {score} {away}"
    return f"⚽ {home} — {away}"


def _description(m: dict) -> str:
    stage = STAGE_RU.get(m.get("stage", ""), m.get("stage", ""))
    grp = (m.get("group") or "").replace("GROUP_", "Группа ")
    venue = venue_for(m) or m.get("venue") or "уточняется"
    home = m.get("homeTeam", {}).get("name") or "TBD"
    away = m.get("awayTeam", {}).get("name") or "TBD"
    parts = [
        f"{flag(home)} {home} — {away} {flag(away)}",
        "",
    ]
    score = _final_score(m)
    if score:
        note = _duration_note(m)
        result = f"Итог: {home} {score} {away}"
        if note:
            result += f" ({note})"
        parts += [result, ""]
    parts.append(f"Стадия: {stage}")
    if grp:
        parts.append(f"Группа: {grp}")
    if m.get("matchday"):
        parts.append(f"Тур: {m['matchday']}")
    parts.append(f"Город: {venue}")
    return "\n".join(parts)


def _body(m: dict) -> dict:
    start = _parse(m["utcDate"])
    end = start + timedelta(hours=MATCH_DURATION_HOURS)
    summary = _title(m)
    description = _description(m)
    location = venue_for(m)
    # Signature over everything we render, so any content change triggers an update.
    sig = hashlib.md5(
        "|".join([m["utcDate"], summary, location or "", description]).encode("utf-8")
    ).hexdigest()
    body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start.isoformat().replace("+00:00", "Z"), "timeZone": TZ},
        "end": {"dateTime": end.isoformat().replace("+00:00", "Z"), "timeZone": TZ},
        "extendedProperties": {
            "private": {
                P_MANAGED: "1",
                P_MATCH_ID: str(m["id"]),
                P_START: m["utcDate"],
                P_SIG: sig,
                P_FINAL: "1" if _final_score(m) else "0",
            }
        },
        "reminders": {"useDefault": False, "overrides": [{"method": "popup", "minutes": 10}]},
    }
    if location:
        body["location"] = location
    return body


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

    created = updated = skipped = deleted = fetched = 0

    # Upsert every match in the forward window AND every match we already have an
    # event for. Iterating the union of both id sets — not just the bulk API
    # list — is what keeps a managed event fresh after kickoff: the competition
    # feed stops returning older finished matches, so an event whose match has
    # dropped out (`mid` in existing but not in by_id) would otherwise never be
    # revisited and never receive its final score. For those we fetch the match
    # on its own, unless the score has already landed (P_FINAL == "1").
    for mid in sorted(set(by_id) | set(existing)):
        m = by_id.get(mid)
        if m is None:
            priv = existing[mid].get("extendedProperties", {}).get("private", {})
            if priv.get(P_FINAL) == "1":
                skipped += 1  # final score already on the event — nothing to fetch
                continue
            try:
                m = wc_api.match(mid)
                fetched += 1
            except Exception as exc:  # match genuinely gone; leave the event as-is
                log.warning("Could not fetch dropped match %s: %s", mid, exc)
                continue

        if not m.get("utcDate"):
            continue
        when = _parse(m["utcDate"])
        if not (now <= when <= horizon or mid in existing):
            continue
        status = m.get("status")

        if status in {"CANCELLED", "POSTPONED"}:
            if mid in existing:
                service.events().delete(calendarId=calendar_id, eventId=existing[mid]["id"]).execute()
                deleted += 1
                log.info("Deleted event for %s match %s", status, mid)
            continue

        body = _body(m)
        new_sig = body["extendedProperties"]["private"][P_SIG]
        if mid in existing:
            ev = existing[mid]
            priv = ev.get("extendedProperties", {}).get("private", {})
            if priv.get(P_SIG) == new_sig:
                skipped += 1
                continue
            service.events().update(calendarId=calendar_id, eventId=ev["id"], body=body).execute()
            updated += 1
            reason = "time" if priv.get(P_START) != m["utcDate"] else "content"
            log.info("Updated event for match %s (%s changed)", mid, reason)
        else:
            service.events().insert(calendarId=calendar_id, body=body).execute()
            created += 1
            log.info("Created event for match %s at %s", mid, m["utcDate"])

    log.info(
        "Done. created=%d updated=%d skipped=%d deleted=%d fetched=%d",
        created, updated, skipped, deleted, fetched,
    )


if __name__ == "__main__":
    main()
