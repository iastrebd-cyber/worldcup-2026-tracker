"""Generate standings.md (all 12 groups) and, once the group stage is over,
bracket.md (the knockout tree) for the World Cup 2026.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import wc_api
from flags import flag

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("wc")

STAGE_ORDER = [
    ("LAST_32", "1/16 финала"),
    ("LAST_16", "1/8 финала"),
    ("QUARTER_FINALS", "1/4 финала"),
    ("SEMI_FINALS", "1/2 финала"),
    ("THIRD_PLACE", "Матч за 3-е место"),
    ("FINAL", "Финал"),
]


def _gd(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


def build_standings_md(data: dict) -> str:
    lines: list[str] = []
    lines.append("# 🏆 ЧМ-2026 — Турнирные таблицы групп\n")
    lines.append(
        f"_Обновлено: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · "
        "источник: football-data.org_\n"
    )

    groups = [s for s in data.get("standings", []) if s.get("type") == "TOTAL"]
    groups.sort(key=lambda s: s.get("group") or "")

    for s in groups:
        group_name = (s.get("group") or "Группа").replace("Group ", "Группа ")
        lines.append(f"\n## {group_name}\n")
        lines.append("| № |  | Команда | И | В | Н | П | Голы | РМ | О |")
        lines.append("|--:|:--:|:--|--:|--:|--:|--:|:--:|--:|--:|")
        for row in s.get("table", []):
            team = row.get("team", {})
            name = team.get("name", "—")
            lines.append(
                "| {pos} | {fl} | {name} | {p} | {w} | {d} | {l} | {gf}:{ga} | {gd} | **{pts}** |".format(
                    pos=row.get("position", ""),
                    fl=flag(name),
                    name=name,
                    p=row.get("playedGames", 0),
                    w=row.get("won", 0),
                    d=row.get("draw", 0),
                    l=row.get("lost", 0),
                    gf=row.get("goalsFor", 0),
                    ga=row.get("goalsAgainst", 0),
                    gd=_gd(row.get("goalDifference", 0)),
                    pts=row.get("points", 0),
                )
            )

    lines.append("")
    return "\n".join(lines)


def _team_label(team: dict | None) -> str:
    if not team or not team.get("name"):
        return "🏳️ _TBD_"
    name = team["name"]
    return f"{flag(name)} {name}"


def _score(match: dict) -> str:
    ft = (match.get("score") or {}).get("fullTime") or {}
    h, a = ft.get("home"), ft.get("away")
    if h is None or a is None:
        return ""
    return f" **{h}:{a}**"


def build_bracket_md(matches: list[dict]) -> str | None:
    knockout = [m for m in matches if m.get("stage") in {s for s, _ in STAGE_ORDER}]
    if not knockout:
        return None

    lines = ["# 🏆 ЧМ-2026 — Плей-офф\n"]
    lines.append(
        f"_Обновлено: {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC_\n"
    )
    any_team = False
    for stage, title in STAGE_ORDER:
        stage_matches = [m for m in knockout if m.get("stage") == stage]
        if not stage_matches:
            continue
        lines.append(f"\n## {title}\n")
        stage_matches.sort(key=lambda m: m.get("utcDate") or "")
        for m in stage_matches:
            home, away = m.get("homeTeam"), m.get("awayTeam")
            if (home and home.get("name")) or (away and away.get("name")):
                any_team = True
            date = (m.get("utcDate") or "")[:10] or "дата TBD"
            lines.append(
                f"- {date}: {_team_label(home)} — {_team_label(away)}{_score(m)}"
            )

    if not any_team:
        lines.append("\n_Пары плей-офф ещё не определены — групповой этап продолжается._\n")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    log.info("Fetching standings...")
    standings_data = wc_api.standings()
    with open("standings.md", "w", encoding="utf-8") as f:
        f.write(build_standings_md(standings_data))
    log.info("Wrote standings.md")

    log.info("Fetching matches for bracket...")
    matches = wc_api.matches().get("matches", [])
    group_matches = [m for m in matches if m.get("stage") == "GROUP_STAGE"]
    group_done = bool(group_matches) and all(
        m.get("status") == "FINISHED" for m in group_matches
    )

    bracket = build_bracket_md(matches)
    if bracket is not None and (group_done or any(
        (m.get("homeTeam") or {}).get("name") and m.get("stage") != "GROUP_STAGE"
        for m in matches
    )):
        with open("bracket.md", "w", encoding="utf-8") as f:
            f.write(bracket)
        log.info("Wrote bracket.md (group stage finished=%s)", group_done)
    else:
        log.info("Group stage not finished and no knockout pairings yet; skipping bracket.md")


if __name__ == "__main__":
    main()
