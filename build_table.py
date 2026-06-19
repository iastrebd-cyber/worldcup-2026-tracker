"""Build docs/index.html — the auto-updating World Cup 2026 standings page.

Two modes:
  * default        — pull live data from football-data.org (needs the
                     FOOTBALL_DATA_API_KEY env var)
  * --mock         — read the offline snapshot from mock_data.py

The page is fully static (no <script>): all rendering happens here at build
time. Output goes to docs/index.html, ready for GitHub Pages.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

API_BASE = "https://api.football-data.org/v4"
TEMPLATE = "template.html"
OUTPUT_DIR = "docs"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")

GROUPS_MARKER = "<!-- GROUPS -->"
UPDATED_MARKER = "<!-- UPDATED -->"

# Subdivision flags (England, Scotland) need tag-sequence emoji.
_FLAG_ENGLAND = "🏴\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f"
_FLAG_SCOTLAND = "🏴\U000e0067\U000e0062\U000e0073\U000e0063\U000e0074\U000e007f"

# Map the English team names the API can return -> (Russian name, flag emoji).
# Alternative spellings point at the same value.
TEAMS: dict[str, tuple[str, str]] = {
    # Group A
    "Mexico": ("Мексика", "🇲🇽"),
    "South Korea": ("Южная Корея", "🇰🇷"),
    "Korea Republic": ("Южная Корея", "🇰🇷"),
    "Czechia": ("Чехия", "🇨🇿"),
    "South Africa": ("ЮАР", "🇿🇦"),
    # Group B
    "Canada": ("Канада", "🇨🇦"),
    "Bosnia and Herzegovina": ("Босния и Герцеговина", "🇧🇦"),
    "Bosnia-Herzegovina": ("Босния и Герцеговина", "🇧🇦"),
    "Qatar": ("Катар", "🇶🇦"),
    "Switzerland": ("Швейцария", "🇨🇭"),
    # Group C
    "Scotland": ("Шотландия", _FLAG_SCOTLAND),
    "Morocco": ("Марокко", "🇲🇦"),
    "Brazil": ("Бразилия", "🇧🇷"),
    "Haiti": ("Гаити", "🇭🇹"),
    # Group D
    "United States": ("США", "🇺🇸"),
    "USA": ("США", "🇺🇸"),
    "Australia": ("Австралия", "🇦🇺"),
    "Türkiye": ("Турция", "🇹🇷"),
    "Turkey": ("Турция", "🇹🇷"),
    "Paraguay": ("Парагвай", "🇵🇾"),
    # Group E
    "Germany": ("Германия", "🇩🇪"),
    "Ivory Coast": ("Кот-д’Ивуар", "🇨🇮"),
    "Côte d’Ivoire": ("Кот-д’Ивуар", "🇨🇮"),
    "Côte d'Ivoire": ("Кот-д’Ивуар", "🇨🇮"),
    "Ecuador": ("Эквадор", "🇪🇨"),
    "Curaçao": ("Кюрасао", "🇨🇼"),
    "Curacao": ("Кюрасао", "🇨🇼"),
    # Group F
    "Sweden": ("Швеция", "🇸🇪"),
    "Japan": ("Япония", "🇯🇵"),
    "Netherlands": ("Нидерланды", "🇳🇱"),
    "Tunisia": ("Тунис", "🇹🇳"),
    # Group G
    "New Zealand": ("Новая Зеландия", "🇳🇿"),
    "Iran": ("Иран", "🇮🇷"),
    "IR Iran": ("Иран", "🇮🇷"),
    "Egypt": ("Египет", "🇪🇬"),
    "Belgium": ("Бельгия", "🇧🇪"),
    # Group H
    "Saudi Arabia": ("Саудовская Аравия", "🇸🇦"),
    "Uruguay": ("Уругвай", "🇺🇾"),
    "Spain": ("Испания", "🇪🇸"),
    "Cape Verde": ("Кабо-Верде", "🇨🇻"),
    "Cabo Verde": ("Кабо-Верде", "🇨🇻"),
    "Cape Verde Islands": ("Кабо-Верде", "🇨🇻"),
    # Group I
    "Norway": ("Норвегия", "🇳🇴"),
    "France": ("Франция", "🇫🇷"),
    "Senegal": ("Сенегал", "🇸🇳"),
    "Iraq": ("Ирак", "🇮🇶"),
    # Group J
    "Argentina": ("Аргентина", "🇦🇷"),
    "Austria": ("Австрия", "🇦🇹"),
    "Jordan": ("Иордания", "🇯🇴"),
    "Algeria": ("Алжир", "🇩🇿"),
    # Group K
    "Colombia": ("Колумбия", "🇨🇴"),
    "Portugal": ("Португалия", "🇵🇹"),
    "DR Congo": ("ДР Конго", "🇨🇩"),
    "Congo DR": ("ДР Конго", "🇨🇩"),
    "Uzbekistan": ("Узбекистан", "🇺🇿"),
    # Group L
    "England": ("Англия", _FLAG_ENGLAND),
    "Ghana": ("Гана", "🇬🇭"),
    "Panama": ("Панама", "🇵🇦"),
    "Croatia": ("Хорватия", "🇭🇷"),
}


def team_label(name_en: str | None) -> tuple[str, str]:
    """Return (russian_name, flag) for an API team name, with a safe fallback."""
    if not name_en:
        return ("—", "🏳️")
    ru, fl = TEAMS.get(name_en, (name_en, "🏳️"))
    return (ru, fl)


# --------------------------------------------------------------------------
# Data loading -> a common shape:
#   groups = { "A": {"rows": [row, ...], "matches": [(home, hg, ag, away), ...]} }
#   row = (name_en, played, won, draw, lost, gf, ga, points)
# --------------------------------------------------------------------------
def load_mock() -> dict[str, dict]:
    import mock_data

    groups: dict[str, dict] = {}
    for letter, rows in mock_data.GROUPS.items():
        groups[letter] = {
            "rows": list(rows),
            "matches": list(mock_data.MATCHES.get(letter, [])),
        }
    return groups


def _group_letter(raw: str | None) -> str:
    """Normalise 'Group A' / 'GROUP_A' -> 'A'."""
    if not raw:
        return ""
    return raw.replace("GROUP_", "").replace("Group ", "").strip()


def load_api() -> dict[str, dict]:
    key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not key:
        sys.exit("FOOTBALL_DATA_API_KEY is not set. Use --mock for offline builds.")
    headers = {"X-Auth-Token": key}

    standings_resp = requests.get(
        f"{API_BASE}/competitions/WC/standings", headers=headers, timeout=30
    )
    standings_resp.raise_for_status()
    matches_resp = requests.get(
        f"{API_BASE}/competitions/WC/matches", headers=headers, timeout=30
    )
    matches_resp.raise_for_status()

    groups: dict[str, dict] = {}

    for block in standings_resp.json().get("standings", []):
        if block.get("type") != "TOTAL":
            continue
        letter = _group_letter(block.get("group"))
        if not letter:
            continue
        rows = []
        for r in block.get("table", []):
            rows.append(
                (
                    (r.get("team") or {}).get("name"),
                    r.get("playedGames", 0),
                    r.get("won", 0),
                    r.get("draw", 0),
                    r.get("lost", 0),
                    r.get("goalsFor", 0),
                    r.get("goalsAgainst", 0),
                    r.get("points", 0),
                )
            )
        groups.setdefault(letter, {"rows": [], "matches": []})["rows"] = rows

    matches_by_group: dict[str, list] = defaultdict(list)
    for m in matches_resp.json().get("matches", []):
        if m.get("stage") != "GROUP_STAGE" or m.get("status") != "FINISHED":
            continue
        letter = _group_letter(m.get("group"))
        ft = (m.get("score") or {}).get("fullTime") or {}
        matches_by_group[letter].append(
            (
                (m.get("homeTeam") or {}).get("name"),
                ft.get("home"),
                ft.get("away"),
                (m.get("awayTeam") or {}).get("name"),
            )
        )

    for letter, ms in matches_by_group.items():
        groups.setdefault(letter, {"rows": [], "matches": []})["matches"] = ms

    return groups


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------
def _gd_cell(gf: int, ga: int) -> str:
    gd = gf - ga
    if gd > 0:
        return f'<td class="gd gd--pos">+{gd}</td>'
    if gd < 0:
        return f'<td class="gd gd--neg">{gd}</td>'
    return '<td class="gd gd--zero">0</td>'


def render_match(home_en, hg, ag, away_en) -> str:
    h_ru, h_fl = team_label(home_en)
    a_ru, a_fl = team_label(away_en)
    if hg is None or ag is None:
        return ""
    if hg == ag:
        h_cls = a_cls = "team--draw"
        score_cls = "score--draw"
    elif hg > ag:
        h_cls, a_cls = "team--win", "team--lose"
        score_cls = "score--win"
    else:
        h_cls, a_cls = "team--lose", "team--win"
        score_cls = "score--win"
    return (
        '<li class="match">'
        f'<span class="team team--home {h_cls}"><span class="fl">{h_fl}</span>{h_ru}</span>'
        f'<span class="score {score_cls}">{hg}:{ag}</span>'
        f'<span class="team team--away {a_cls}"><span class="fl">{a_fl}</span>{a_ru}</span>'
        '</li>'
    )


def render_card(letter: str, data: dict) -> str:
    rows = data.get("rows", [])
    matches = data.get("matches", [])

    body_rows = []
    for pos, row in enumerate(rows, start=1):
        name_en, played, won, draw, lost, gf, ga, pts = row
        ru, fl = team_label(name_en)
        body_rows.append(
            f'<tr class="pos-{pos}">'
            f'<td class="c-team"><span class="fl">{fl}</span>{ru}</td>'
            f'<td>{played}</td>'
            f'<td class="c-opt">{won}</td>'
            f'<td class="c-opt">{draw}</td>'
            f'<td class="c-opt">{lost}</td>'
            f'<td class="c-opt">{gf}:{ga}</td>'
            f'{_gd_cell(gf, ga)}'
            f'<td class="pts">{pts}</td>'
            '</tr>'
        )

    match_items = [render_match(*m) for m in matches]
    match_items = [m for m in match_items if m]
    if match_items:
        matches_html = '<ul class="matches">' + "".join(match_items) + "</ul>"
    else:
        matches_html = (
            '<ul class="matches"><li class="matches__empty">Матчей пока нет</li></ul>'
        )

    return (
        '<article class="group">'
        '<div class="group__head">'
        f'<span class="group__badge">{letter}</span>'
        f'<h3 class="group__title">Группа {letter}</h3>'
        '</div>'
        '<table class="tbl">'
        '<thead><tr>'
        '<th class="c-team">Команда</th><th>И</th>'
        '<th class="c-opt">В</th><th class="c-opt">Н</th><th class="c-opt">П</th>'
        '<th class="c-opt">Мячи</th><th>РМ</th><th>О</th>'
        '</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        '</table>'
        f'{matches_html}'
        '</article>'
    )


def render_groups(groups: dict[str, dict]) -> str:
    cards = [render_card(letter, groups[letter]) for letter in sorted(groups)]
    return "\n".join(cards)


def updated_stamp() -> str:
    now = datetime.now(ZoneInfo("America/New_York"))
    return f"{now:%d.%m.%Y, %H:%M} (EDT, Майами)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the WC-2026 standings page.")
    parser.add_argument(
        "--mock", action="store_true", help="use mock_data.py instead of the live API"
    )
    args = parser.parse_args()

    groups = load_mock() if args.mock else load_api()

    with open(TEMPLATE, encoding="utf-8") as f:
        template = f.read()

    html = template.replace(GROUPS_MARKER, render_groups(groups))
    html = html.replace(UPDATED_MARKER, updated_stamp())

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Wrote {OUTPUT_FILE} ({len(groups)} groups).")


if __name__ == "__main__":
    main()
