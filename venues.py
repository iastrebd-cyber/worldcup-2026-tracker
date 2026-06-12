"""Host city / stadium for each World Cup 2026 match.

The football-data.org API exposes a `venue` field but it is empty for every
WC-2026 match, so cities are provided here from the published schedule.

Group-stage venues are keyed by (group, unordered team pair) — each pair meets
exactly once per group, so the key is unique and independent of home/away order
or kickoff timezone. This mapping was verified to cover all 72 group matches.

Knockout venues are not yet mapped (teams are TBD and matches are weeks away);
`venue_for` returns None for them, and callers fall back to "уточняется".
"""
from __future__ import annotations

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

# group | team1 | team2 | city  (from the published 2026 group-stage schedule)
_RAW = """A|Mexico|South Africa|Guadalajara
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


def _canon(name: str) -> str:
    name = name.strip()
    return _ALIAS.get(name, name)


def _build() -> dict:
    table: dict = {}
    for line in _RAW.strip().splitlines():
        group, t1, t2, city = (x.strip() for x in line.split("|"))
        table[(group, frozenset({_canon(t1), _canon(t2)}))] = city
    return table


_GROUP_VENUES = _build()


def venue_for(match: dict, with_stadium: bool = True) -> str | None:
    """Return "City (Stadium)" (or just "City") for a match, or None if unknown."""
    if match.get("stage") != "GROUP_STAGE":
        return None
    group = (match.get("group") or "").replace("GROUP_", "")
    home = (match.get("homeTeam") or {}).get("name")
    away = (match.get("awayTeam") or {}).get("name")
    if not home or not away:
        return None
    city_key = _GROUP_VENUES.get((group, frozenset({home, away})))
    if not city_key:
        return None
    ru, stadium = CITY[city_key]
    return f"{ru} ({stadium})" if with_stadium else ru
