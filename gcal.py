"""Google Calendar service helper.

Builds an authenticated Calendar API client from a service-account JSON blob
provided either as a raw JSON string (env GOOGLE_SERVICE_ACCOUNT_JSON) or a
path to a key file (env GOOGLE_SERVICE_ACCOUNT_FILE / local sa-key.json).
"""
from __future__ import annotations

import json
import logging
import os

from google.oauth2 import service_account
from googleapiclient.discovery import build

log = logging.getLogger("wc")

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _load_credentials() -> service_account.Credentials:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw:
        # Some secret stores prepend a UTF-8 BOM; round-tripping through
        # utf-8-sig strips it cleanly without depending on a literal char.
        info = json.loads(raw.encode("utf-8").decode("utf-8-sig").strip())
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "sa-key.json")
    if os.path.exists(path):
        return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)

    raise SystemExit(
        "No service-account credentials found. Set GOOGLE_SERVICE_ACCOUNT_JSON "
        "or provide sa-key.json / GOOGLE_SERVICE_ACCOUNT_FILE."
    )


def calendar_service():
    creds = _load_credentials()
    log.info("Authenticated as service account %s", creds.service_account_email)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)
