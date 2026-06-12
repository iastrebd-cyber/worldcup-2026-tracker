"""Host city / stadium for each World Cup 2026 match.

The football-data.org API exposes a `venue` field but it is empty for every
WC-2026 match, so cities are provided here from the published schedule.

Group stage: keyed by (group, unordered team pair) — each pair meets exactly
once per group, so the key is unique regardless of home/away order or timezone.
Verified to cover all 72 group matches.

Knockout stage: teams are TBD, so matches are keyed by their exact kickoff
instant (UTC). The instant is derived here from the venue's stadium and local
kickoff time, and was verified to match all 32 football-data knockout fixtures.
If a kickoff time later shifts, the lookup simply misses and callers fall back
to "уточняется" — never a wrong city.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

_UTC = ZoneInfo("UTC")

# football-data team names differ slightly from the schedule source.
_ALIAS = {
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "Turkiye": "Turkey",
    "Curacao": "Curaçao",
    "Cape Verde": "Cape Verde Islands",
    "Democratic Republic of Congo": "Congo DR",
    "USA": "United States",
}

# Schedule city -> (Russian display name, stadium)
CITY = {
    "Mexico City": ("Мехико", "Estadio Azteca"),
    "Guadalajara": ("Гвадалахара", "Estadio Akron"),
    "Monterrey": ("Монтеррей", "Estadio BBVA"),
    "Toronto": ("Торонто", "BMO Field"),
    "Vancouver": ("Ванкувер", "BC Place"),
    "Seattle": ("Сиэтл", "Lumen Field"),
    "San Francisco": ("Сан-Франциско", "Levi's Stadium"),
    "Los Angeles": ("Лос-Анджелес", "SoFi Stadium"),
    "New York": ("Нью-Йорк", "MetLife Stadium"),
    "Boston": ("Бостон", "Gillette Stadium"),
    "Philadelphia": ("Филадельфия", "Lincoln Financial Field"),
    "Dallas": ("Даллас", "AT&T Stadium"),
    "Houston": ("Хьюстон", "NRG Stadium"),
    "Kansas City": ("Канзас-Сити", "Arrowhead Stadium"),
    "Miami": ("Майами", "Hard Rock Stadium"),
    "Atlanta": ("Атланта", "Mercedes-Benz Stadium"),
}

# ---------------------------------------------------------------------------
# Group stage: group | team1 | team2 | city
# ---------------------------------------------------------------------------
_GROUP_RAW = """A|Mexico|South Africa|Guadalajara
A|South Korea|Czechia|Atlanta
A|Czechia|South Africa|Atlanta
A|Mexico|South Korea|Guadalajara
A|Czechia|Mexico|Mexico City
A|South Africa|South Korea|Monterrey
B|Canada|Bosnia and Herzegovina|Toronto
B|Qatar|Switzerland|San Francisco
B|Switzerland|Bosnia and Herzegovina|Los Angeles
B|Canada|Qatar|Vancouver
B|Switzerland|Canada|Vancouver
B|Bosnia and Herzegovina|Qatar|Seattle
C|Brazil|Morocco|New York
C|Haiti|Scotland|Boston
C|Scotland|Morocco|Boston
C|Brazil|Haiti|Philadelphia
C|Scotland|Brazil|Miami
C|Morocco|Haiti|Atlanta
D|USA|Paraguay|Los Angeles
D|Australia|Turkiye|Vancouver
D|USA|Australia|Seattle
D|Turkiye|Paraguay|San Francisco
D|Turkiye|USA|Los Angeles
D|Paraguay|Australia|San Francisco
E|Germany|Curacao|Houston
E|Ivory Coast|Ecuador|Philadelphia
E|Germany|Ivory Coast|Toronto
E|Ecuador|Curacao|Kansas City
E|Ecuador|Germany|New York
E|Curacao|Ivory Coast|Philadelphia
F|Netherlands|Japan|Dallas
F|Sweden|Tunisia|Monterrey
F|Netherlands|Sweden|Houston
F|Tunisia|Japan|Monterrey
F|Japan|Sweden|Dallas
F|Tunisia|Netherlands|Kansas City
G|Iran|New Zealand|Los Angeles
G|Belgium|Egypt|Seattle
G|Belgium|Iran|Los Angeles
G|New Zealand|Egypt|Vancouver
G|Egypt|Iran|Seattle
G|New Zealand|Belgium|Vancouver
H|Spain|Cape Verde|Atlanta
H|Saudi Arabia|Uruguay|Miami
H|Spain|Saudi Arabia|Atlanta
H|Uruguay|Cape Verde|Miami
H|Cape Verde|Saudi Arabia|Houston
H|Uruguay|Spain|Guadalajara
I|France|Senegal|New York
I|Iraq|Norway|Boston
I|France|Iraq|Philadelphia
I|Norway|Senegal|New York
I|Norway|France|Boston
I|Senegal|Iraq|Toronto
J|Argentina|Algeria|Kansas City
J|Austria|Jordan|San Francisco
J|Argentina|Austria|Dallas
J|Jordan|Algeria|San Francisco
J|Algeria|Austria|Kansas City
J|Jordan|Argentina|Dallas
K|Portugal|Democratic Republic of Congo|Houston
K|Uzbekistan|Colombia|Mexico City
K|Portugal|Uzbekistan|Houston
K|Colombia|Democratic Republic of Congo|Guadalajara
K|Colombia|Portugal|Miami
K|Democratic Republic of Congo|Uzbekistan|Atlanta
L|England|Croatia|Dallas
L|Ghana|Panama|Toronto
L|England|Ghana|Boston
L|Panama|Croatia|Toronto
L|Panama|England|New York
L|Croatia|Ghana|Philadelphia"""

# ---------------------------------------------------------------------------
# Knockout stage: stadium -> (Russian city, IANA timezone). The stadium is the
# trustworthy anchor; the city/timezone are derived from it (not the source).
# ---------------------------------------------------------------------------
_STADIUM = {
    "SoFi Stadium": ("Лос-Анджелес", "America/Los_Angeles"),
    "Gillette Stadium": ("Бостон", "America/New_York"),
    "Estadio BBVA": ("Монтеррей", "America/Monterrey"),
    "NRG Stadium": ("Хьюстон", "America/Chicago"),
    "AT&T Stadium": ("Даллас", "America/Chicago"),
    "MetLife Stadium": ("Нью-Йорк", "America/New_York"),
    "Estadio Azteca": ("Мехико", "America/Mexico_City"),
    "Mercedes-Benz Stadium": ("Атланта", "America/New_York"),
    "Lumen Field": ("Сиэтл", "America/Los_Angeles"),
    "Levi's Stadium": ("Сан-Франциско", "America/Los_Angeles"),
    "BMO Field": ("Торонто", "America/Toronto"),
    "BC Place": ("Ванкувер", "America/Vancouver"),
    "Hard Rock Stadium": ("Майами", "America/New_York"),
    "Arrowhead Stadium": ("Канзас-Сити", "America/Chicago"),
    "Lincoln Financial Field": ("Филадельфия", "America/New_York"),
}

# date | local kickoff (stadium-local 24h) | stadium
_KNOCKOUT_RAW = """2026-06-28|12:00|SoFi Stadium
2026-06-29|16:30|Gillette Stadium
2026-06-29|19:00|Estadio BBVA
2026-06-29|12:00|NRG Stadium
2026-06-30|12:00|AT&T Stadium
2026-06-30|17:00|MetLife Stadium
2026-06-30|19:00|Estadio Azteca
2026-07-01|12:00|Mercedes-Benz Stadium
2026-07-01|13:00|Lumen Field
2026-07-01|17:00|Levi's Stadium
2026-07-02|12:00|SoFi Stadium
2026-07-02|19:00|BMO Field
2026-07-02|20:00|BC Place
2026-07-03|13:00|AT&T Stadium
2026-07-03|18:00|Hard Rock Stadium
2026-07-03|20:30|Arrowhead Stadium
2026-07-04|12:00|NRG Stadium
2026-07-04|17:00|Lincoln Financial Field
2026-07-05|16:00|MetLife Stadium
2026-07-05|18:00|Estadio Azteca
2026-07-06|14:00|AT&T Stadium
2026-07-06|17:00|Lumen Field
2026-07-07|12:00|Mercedes-Benz Stadium
2026-07-07|13:00|BC Place
2026-07-09|16:00|Gillette Stadium
2026-07-10|12:00|SoFi Stadium
2026-07-11|17:00|Hard Rock Stadium
2026-07-11|20:00|Arrowhead Stadium
2026-07-14|14:00|AT&T Stadium
2026-07-15|15:00|Mercedes-Benz Stadium
2026-07-18|17:00|Hard Rock Stadium
2026-07-19|15:00|MetLife Stadium"""


def _canon(name: str) -> str:
    name = name.strip()
    return _ALIAS.get(name, name)


def _build_group() -> dict:
    table: dict = {}
    for line in _GROUP_RAW.strip().splitlines():
        group, t1, t2, city = (x.strip() for x in line.split("|"))
        table[(group, frozenset({_canon(t1), _canon(t2)}))] = city
    return table


def _build_knockout() -> dict:
    table: dict = {}
    for line in _KNOCKOUT_RAW.strip().splitlines():
        date, local_time, stadium = (x.strip() for x in line.split("|"))
        city, tz = _STADIUM[stadium]
        local = datetime.strptime(f"{date} {local_time}", "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo(tz))
        iso = local.astimezone(_UTC).strftime("%Y-%m-%dT%H:%M:00Z")
        table[iso] = (city, stadium)
    return table


_GROUP_VENUES = _build_group()
_KNOCKOUT_VENUES = _build_knockout()


def venue_for(match: dict, with_stadium: bool = True) -> str | None:
    """Return "City (Stadium)" (or just "City") for a match, or None if unknown."""
    if match.get("stage") == "GROUP_STAGE":
        group = (match.get("group") or "").replace("GROUP_", "")
        home = (match.get("homeTeam") or {}).get("name")
        away = (match.get("awayTeam") or {}).get("name")
        if not home or not away:
            return None
        city_key = _GROUP_VENUES.get((group, frozenset({home, away})))
        if not city_key:
            return None
        city, stadium = CITY[city_key]
    else:
        found = _KNOCKOUT_VENUES.get(match.get("utcDate"))
        if not found:
            return None
        city, stadium = found
    return f"{city} ({stadium})" if with_stadium else city
