"""Offline snapshot of the World Cup 2026 group stage as of 18 June 2026.

Used by ``build_table.py --mock`` so the page can be regenerated without
calling football-data.org.

Shapes
------
Standings row : (english_name, played, won, draw, lost, goals_for, goals_against, points)
Match         : (home_english, home_goals, away_goals, away_english)

Teams in each group's list are already ordered by table position.
"""
from __future__ import annotations

# group letter -> list of standings rows
GROUPS: dict[str, list[tuple]] = {
    "A": [
        ("Mexico", 1, 1, 0, 0, 2, 0, 3),
        ("South Korea", 1, 1, 0, 0, 2, 1, 3),
        ("Czechia", 1, 0, 0, 1, 1, 2, 0),
        ("South Africa", 1, 0, 0, 1, 0, 2, 0),
    ],
    "B": [
        ("Canada", 1, 0, 1, 0, 1, 1, 1),
        ("Bosnia and Herzegovina", 1, 0, 1, 0, 1, 1, 1),
        ("Qatar", 1, 0, 1, 0, 1, 1, 1),
        ("Switzerland", 1, 0, 1, 0, 1, 1, 1),
    ],
    "C": [
        ("Scotland", 1, 1, 0, 0, 1, 0, 3),
        ("Morocco", 1, 0, 1, 0, 1, 1, 1),
        ("Brazil", 1, 0, 1, 0, 1, 1, 1),
        ("Haiti", 1, 0, 0, 1, 0, 1, 0),
    ],
    "D": [
        ("United States", 1, 1, 0, 0, 4, 1, 3),
        ("Australia", 1, 1, 0, 0, 2, 0, 3),
        ("Türkiye", 1, 0, 0, 1, 0, 2, 0),
        ("Paraguay", 1, 0, 0, 1, 1, 4, 0),
    ],
    "E": [
        ("Germany", 1, 1, 0, 0, 7, 1, 3),
        ("Ivory Coast", 1, 1, 0, 0, 1, 0, 3),
        ("Ecuador", 1, 0, 0, 1, 0, 1, 0),
        ("Curaçao", 1, 0, 0, 1, 1, 7, 0),
    ],
    "F": [
        ("Sweden", 1, 1, 0, 0, 5, 1, 3),
        ("Japan", 1, 0, 1, 0, 2, 2, 1),
        ("Netherlands", 1, 0, 1, 0, 2, 2, 1),
        ("Tunisia", 1, 0, 0, 1, 1, 5, 0),
    ],
    "G": [
        ("New Zealand", 1, 0, 1, 0, 2, 2, 1),
        ("Iran", 1, 0, 1, 0, 2, 2, 1),
        ("Egypt", 1, 0, 1, 0, 1, 1, 1),
        ("Belgium", 1, 0, 1, 0, 1, 1, 1),
    ],
    "H": [
        ("Saudi Arabia", 1, 0, 1, 0, 1, 1, 1),
        ("Uruguay", 1, 0, 1, 0, 1, 1, 1),
        ("Spain", 1, 0, 1, 0, 0, 0, 1),
        ("Cape Verde", 1, 0, 1, 0, 0, 0, 1),
    ],
    "I": [
        ("Norway", 1, 1, 0, 0, 4, 1, 3),
        ("France", 1, 1, 0, 0, 3, 1, 3),
        ("Senegal", 1, 0, 0, 1, 1, 3, 0),
        ("Iraq", 1, 0, 0, 1, 1, 4, 0),
    ],
    "J": [
        ("Argentina", 1, 1, 0, 0, 3, 0, 3),
        ("Austria", 1, 1, 0, 0, 3, 1, 3),
        ("Jordan", 1, 0, 0, 1, 1, 3, 0),
        ("Algeria", 1, 0, 0, 1, 0, 3, 0),
    ],
    "K": [
        ("Colombia", 1, 1, 0, 0, 3, 1, 3),
        ("Portugal", 1, 0, 1, 0, 1, 1, 1),
        ("DR Congo", 1, 0, 1, 0, 1, 1, 1),
        ("Uzbekistan", 1, 0, 0, 1, 1, 3, 0),
    ],
    "L": [
        ("England", 1, 1, 0, 0, 4, 2, 3),
        ("Ghana", 1, 1, 0, 0, 1, 0, 3),
        ("Panama", 1, 0, 0, 1, 0, 1, 0),
        ("Croatia", 1, 0, 0, 1, 2, 4, 0),
    ],
}

# group letter -> list of finished matches
MATCHES: dict[str, list[tuple]] = {
    "A": [
        ("Mexico", 2, 0, "South Africa"),
        ("South Korea", 2, 1, "Czechia"),
    ],
    "B": [
        ("Canada", 1, 1, "Bosnia and Herzegovina"),
        ("Qatar", 1, 1, "Switzerland"),
    ],
    "C": [
        ("Brazil", 1, 1, "Morocco"),
        ("Scotland", 1, 0, "Haiti"),
    ],
    "D": [
        ("United States", 4, 1, "Paraguay"),
        ("Australia", 2, 0, "Türkiye"),
    ],
    "E": [
        ("Germany", 7, 1, "Curaçao"),
        ("Ivory Coast", 1, 0, "Ecuador"),
    ],
    "F": [
        ("Netherlands", 2, 2, "Japan"),
        ("Sweden", 5, 1, "Tunisia"),
    ],
    "G": [
        ("Belgium", 1, 1, "Egypt"),
        ("Iran", 2, 2, "New Zealand"),
    ],
    "H": [
        ("Spain", 0, 0, "Cape Verde"),
        ("Saudi Arabia", 1, 1, "Uruguay"),
    ],
    "I": [
        ("France", 3, 1, "Senegal"),
        ("Norway", 4, 1, "Iraq"),
    ],
    "J": [
        ("Argentina", 3, 0, "Algeria"),
        ("Austria", 3, 1, "Jordan"),
    ],
    "K": [
        ("Portugal", 1, 1, "DR Congo"),
        ("Colombia", 3, 1, "Uzbekistan"),
    ],
    "L": [
        ("England", 4, 2, "Croatia"),
        ("Ghana", 1, 0, "Panama"),
    ],
}

# Offline knockout snapshot used only to exercise the bracket renderer
# (`build_table.py --mock`). Live builds pull this straight from the API, which
# fills in each round's pairings and advances winners on its own.
#
# Shape per stage: list of (home_english, home_goals, away_goals, away_english).
# Use None for goals when the match has not been played yet, and None for a team
# name when the slot is still to be determined.
KNOCKOUT: dict[str, list[tuple]] = {
    "LAST_32": [
        ("Mexico", 2, 0, "Switzerland"),
        ("Germany", 3, 1, "South Korea"),
        ("Brazil", 2, 1, "Japan"),
        ("United States", 1, 0, "Morocco"),
        ("France", 2, 0, "Senegal"),
        ("England", 3, 2, "Ghana"),
        ("Argentina", 2, 1, "Australia"),
        ("Spain", 1, 0, "Uruguay"),
        ("Netherlands", 2, 1, "Sweden"),
        ("Portugal", 2, 0, "Colombia"),
        ("Croatia", 1, 0, "Norway"),
        ("Belgium", 2, 1, "Egypt"),
        ("Canada", 1, 0, "Austria"),
        ("Iran", 2, 1, "New Zealand"),
        ("Scotland", 1, 0, "Haiti"),
        ("Ivory Coast", 2, 1, "Ecuador"),
    ],
    "LAST_16": [
        ("Mexico", 1, 0, "Germany"),
        ("Brazil", 2, 1, "United States"),
        ("France", 2, 0, "England"),
        ("Argentina", 1, 0, "Spain"),
        ("Netherlands", 2, 1, "Portugal"),
        ("Croatia", 1, 0, "Belgium"),
        ("Canada", 2, 1, "Iran"),
        ("Scotland", 1, 0, "Ivory Coast"),
    ],
    "QUARTER_FINALS": [
        ("Mexico", 0, 2, "Brazil"),
        ("France", 1, 2, "Argentina"),
        ("Netherlands", 2, 1, "Croatia"),
        ("Canada", 1, 0, "Scotland"),
    ],
    "SEMI_FINALS": [
        ("Brazil", 1, 2, "Argentina"),
        ("Netherlands", 2, 0, "Canada"),
    ],
    "FINAL": [
        ("Argentina", 2, 1, "Netherlands"),
    ],
    "THIRD_PLACE": [
        ("Brazil", 3, 1, "Canada"),
    ],
}
