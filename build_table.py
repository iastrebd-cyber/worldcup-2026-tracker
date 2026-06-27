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
BRACKET_MARKER = "<!-- BRACKET -->"
UPDATED_MARKER = "<!-- UPDATED -->"

# Knockout rounds as football-data.org names them, in tournament order, with the
# display title, the date range, and how many ties the round holds (used to draw
# empty placeholder ties before a round's fixtures exist in the feed).
KNOCKOUT_STAGES = [
    ("LAST_32", "1/16 финала", "28 июня – 3 июля", 16),
    ("LAST_16", "1/8 финала", "4 – 7 июля", 8),
    ("QUARTER_FINALS", "1/4 финала", "9 – 11 июля", 4),
    ("SEMI_FINALS", "1/2 финала", "14 – 15 июля", 2),
]
# Stages rendered inside the final column rather than as their own round.
FINAL_STAGE = "FINAL"
THIRD_PLACE_STAGE = "THIRD_PLACE"
ALL_KNOCKOUT_STAGES = (
    [s for s, *_ in KNOCKOUT_STAGES] + [FINAL_STAGE, THIRD_PLACE_STAGE]
)

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
#   knockout = { "LAST_32": [tie, ...], ... }
#   tie = {"home": name_en|None, "away": name_en|None,
#          "hg": int|None, "ag": int|None, "winner": "HOME_TEAM"|"AWAY_TEAM"|None,
#          "date": "YYYY-MM-DD"|None}
# --------------------------------------------------------------------------
def _tie_from_tuple(t: tuple) -> dict:
    """Normalise a mock (home, hg, ag, away[, date]) tuple into a tie dict."""
    home, hg, ag, away = t[0], t[1], t[2], t[3]
    date = t[4] if len(t) > 4 else None
    winner = None
    if hg is not None and ag is not None:
        winner = "HOME_TEAM" if hg > ag else "AWAY_TEAM" if ag > hg else "DRAW"
    return {"home": home, "away": away, "hg": hg, "ag": ag,
            "winner": winner, "date": date}


def load_mock() -> tuple[dict[str, dict], dict[str, list]]:
    import mock_data

    groups: dict[str, dict] = {}
    for letter, rows in mock_data.GROUPS.items():
        groups[letter] = {
            "rows": list(rows),
            "matches": list(mock_data.MATCHES.get(letter, [])),
        }

    knockout: dict[str, list] = {}
    for stage, ties in getattr(mock_data, "KNOCKOUT", {}).items():
        knockout[stage] = [_tie_from_tuple(t) for t in ties]
    return groups, knockout


def _group_letter(raw: str | None) -> str:
    """Normalise 'Group A' / 'GROUP_A' -> 'A'."""
    if not raw:
        return ""
    return raw.replace("GROUP_", "").replace("Group ", "").strip()


def load_api() -> tuple[dict[str, dict], dict[str, list]]:
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
    knockout: dict[str, list] = defaultdict(list)
    for m in matches_resp.json().get("matches", []):
        stage = m.get("stage")
        score = m.get("score") or {}
        ft = score.get("fullTime") or {}
        if stage == "GROUP_STAGE":
            if m.get("status") != "FINISHED":
                continue
            letter = _group_letter(m.get("group"))
            matches_by_group[letter].append(
                (
                    (m.get("homeTeam") or {}).get("name"),
                    ft.get("home"),
                    ft.get("away"),
                    (m.get("awayTeam") or {}).get("name"),
                )
            )
        elif stage in ALL_KNOCKOUT_STAGES:
            knockout[stage].append(
                {
                    "home": (m.get("homeTeam") or {}).get("name"),
                    "away": (m.get("awayTeam") or {}).get("name"),
                    "hg": ft.get("home"),
                    "ag": ft.get("away"),
                    # score.winner reflects the real result incl. extra time /
                    # penalties; fall back to comparing goals.
                    "winner": score.get("winner"),
                    "date": (m.get("utcDate") or "")[:10] or None,
                }
            )

    for letter, ms in matches_by_group.items():
        groups.setdefault(letter, {"rows": [], "matches": []})["matches"] = ms

    # Keep each knockout round in kick-off order so ties read top-to-bottom.
    for stage, ties in knockout.items():
        ties.sort(key=lambda t: t.get("date") or "")

    return groups, dict(knockout)


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


# --------------------------------------------------------------------------
# Bracket rendering
# --------------------------------------------------------------------------
def _tie_winner(tie: dict) -> str | None:
    """Return 'HOME'/'AWAY'/None for a knockout tie."""
    w = tie.get("winner")
    if w == "HOME_TEAM":
        return "HOME"
    if w == "AWAY_TEAM":
        return "AWAY"
    hg, ag = tie.get("hg"), tie.get("ag")
    if hg is not None and ag is not None and hg != ag:
        return "HOME" if hg > ag else "AWAY"
    return None


def _tie_team(name_en, side_cls: str) -> str:
    ru, fl = team_label(name_en)
    return (
        f'<span class="tie__team {side_cls}">'
        f'<span class="tie__name"><span class="fl">{fl}</span>{ru}</span>'
        '</span>'
    )


def render_tie(tie: dict) -> str:
    """One knockout pairing: two teams stacked around a score/date/VS."""
    hg, ag = tie.get("hg"), tie.get("ag")
    decided = hg is not None and ag is not None
    win = _tie_winner(tie)

    h_cls = "tie__team--win" if win == "HOME" else "tie__team--lose" if win else ""
    a_cls = "tie__team--win" if win == "AWAY" else "tie__team--lose" if win else ""

    if decided:
        middle = f'<span class="tie__vs tie__vs--score">{hg}:{ag}</span>'
    else:
        label = tie.get("date") or "VS"
        middle = f'<span class="tie__vs">{label}</span>'

    tbd = "" if (tie.get("home") or tie.get("away")) else " tie--tbd"
    return (
        f'<div class="tie{tbd}">'
        f'{_tie_team(tie.get("home"), h_cls)}'
        f'{middle}'
        f'{_tie_team(tie.get("away"), a_cls)}'
        '</div>'
    )


def _placeholder_tie() -> str:
    return (
        '<div class="tie tie--tbd">'
        '<span class="tie__team"><span class="tie__name">—</span></span>'
        '<span class="tie__vs">VS</span>'
        '<span class="tie__team"><span class="tie__name">—</span></span>'
        '</div>'
    )


def _round_column(title: str, dates: str, ties_html: str, extra_cls: str = "") -> str:
    return (
        f'<div class="round{extra_cls}">'
        '<div class="round__head">'
        f'<h3 class="round__title">{title}</h3>'
        f'<div class="round__dates">{dates}</div>'
        '</div>'
        f'<div class="round__body">{ties_html}</div>'
        '</div>'
    )


def render_final_round(knockout: dict[str, list]) -> str:
    finals = knockout.get(FINAL_STAGE, [])
    thirds = knockout.get(THIRD_PLACE_STAGE, [])

    final_tie = render_tie(finals[0]) if finals else ""

    third_html = '<p>Матч за 3-е место — 18 июля</p>'
    if thirds:
        t = thirds[0]
        if t.get("hg") is not None and t.get("ag") is not None:
            win = _tie_winner(t)
            bronze = t.get("home") if win == "HOME" else t.get("away") if win == "AWAY" else None
            ru, fl = team_label(bronze)
            medal = f' — 🥉 {fl}{ru}' if bronze else ""
            third_html = (
                f'<p>3-е место: {t.get("hg")}:{t.get("ag")}{medal}</p>'
            )

    body = (
        '<div class="cup">🏆</div>'
        f'{final_tie}'
        '<div class="final-card">'
        '<h3>Финал</h3>'
        '<p class="big">19 июля</p>'
        '<p>MetLife Stadium</p>'
        '<p>Ист-Резерфорд, Нью-Джерси</p>'
        f'{third_html}'
        '</div>'
    )
    return _round_column("Финал", "19 июля", body, extra_cls=" round--final")


def render_bracket(knockout: dict[str, list]) -> str:
    columns = []
    for stage, title, dates, count in KNOCKOUT_STAGES:
        ties = knockout.get(stage, [])
        if ties:
            ties_html = "".join(render_tie(t) for t in ties)
        else:
            ties_html = "".join(_placeholder_tie() for _ in range(count))
        columns.append(_round_column(title, dates, ties_html))
    columns.append(render_final_round(knockout))
    return "\n".join(columns)


def updated_stamp() -> str:
    now = datetime.now(ZoneInfo("America/New_York"))
    return f"{now:%d.%m.%Y, %H:%M} (EDT, Майами)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the WC-2026 standings page.")
    parser.add_argument(
        "--mock", action="store_true", help="use mock_data.py instead of the live API"
    )
    args = parser.parse_args()

    groups, knockout = load_mock() if args.mock else load_api()

    with open(TEMPLATE, encoding="utf-8") as f:
        template = f.read()

    html = template.replace(GROUPS_MARKER, render_groups(groups))
    html = html.replace(BRACKET_MARKER, render_bracket(knockout))
    html = html.replace(UPDATED_MARKER, updated_stamp())

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    ko_ties = sum(len(v) for v in knockout.values())
    print(f"Wrote {OUTPUT_FILE} ({len(groups)} groups, {ko_ties} knockout ties).")


if __name__ == "__main__":
    main()
