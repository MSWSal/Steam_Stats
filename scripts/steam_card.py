#!/usr/bin/env python3
"""Generate an SVG card showing current Steam status and recent playtime."""
import html
import os
import sys

import requests

API_KEY = os.environ["STEAM_API_KEY"]
STEAM_ID = os.environ["STEAM_ID"]
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "assets/steam-card.svg")

SUMMARY_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
RECENT_URL = "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/"

STATUS_NAMES = {
    0: "Offline",
    1: "Online",
    2: "Busy",
    3: "Away",
    4: "Snooze",
    5: "Looking to trade",
    6: "Looking to play",
}
STATUS_COLORS = {
    0: "#8a8a8a",
    1: "#57cbde",
    2: "#e05d44",
    3: "#e0a94c",
    4: "#8a8a8a",
    5: "#57cbde",
    6: "#57cbde",
}
IN_GAME_COLOR = "#57b85a"


def fetch_summary():
    resp = requests.get(
        SUMMARY_URL,
        params={"key": API_KEY, "steamids": STEAM_ID},
        timeout=15,
    )
    resp.raise_for_status()
    players = resp.json()["response"]["players"]
    if not players:
        raise RuntimeError("Steam API returned no player data — check STEAM_ID and profile privacy.")
    return players[0]


def fetch_recent():
    resp = requests.get(
        RECENT_URL,
        params={"key": API_KEY, "steamid": STEAM_ID, "count": 5},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()["response"]
    return data.get("games", [])


def esc(text):
    return html.escape(str(text), quote=True)


def render_svg(summary, recent_games):
    in_game = "gameextrainfo" in summary
    status_code = summary.get("personastate", 0)
    status_label = STATUS_NAMES.get(status_code, "Unknown")
    persona = summary.get("personaname", "Steam User")

    if in_game:
        headline = f"Playing {summary['gameextrainfo']}"
        dot_color = IN_GAME_COLOR
    else:
        headline = status_label
        dot_color = STATUS_COLORS.get(status_code, "#8a8a8a")

    rows = recent_games[:3]
    row_height = 22
    top_padding = 92
    height = top_padding + max(len(rows), 1) * row_height + 16
    width = 420

    game_lines = []
    y = top_padding
    if rows:
        for game in rows:
            name = esc(game.get("name", "Unknown game"))
            minutes_2w = game.get("playtime_2weeks", 0)
            hours_2w = minutes_2w / 60
            game_lines.append(
                f'<text x="24" y="{y}" class="game">{name}</text>'
                f'<text x="{width - 24}" y="{y}" text-anchor="end" class="hours">{hours_2w:.1f} hrs (2wk)</text>'
            )
            y += row_height
    else:
        game_lines.append(f'<text x="24" y="{y}" class="game">No games played in the last 2 weeks</text>')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    .card {{ fill: #0d1117; stroke: #30363d; stroke-width: 1; }}
    .title {{ font: 600 15px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #c9d1d9; }}
    .headline {{ font: 600 13px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #e6edf3; }}
    .section {{ font: 600 11px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #8b949e; letter-spacing: 0.06em; text-transform: uppercase; }}
    .game {{ font: 400 12px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #c9d1d9; }}
    .hours {{ font: 400 12px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #8b949e; }}
  </style>
  <rect class="card" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="6"/>
  <text x="24" y="30" class="title">{esc(persona)} — Steam Status</text>
  <circle cx="30" cy="54" r="5" fill="{dot_color}"/>
  <text x="42" y="58" class="headline">{esc(headline)}</text>
  <text x="24" y="80" class="section">Recently Played</text>
  {''.join(game_lines)}
</svg>'''
    return svg


def main():
    summary = fetch_summary()
    recent_games = fetch_recent()
    svg = render_svg(summary, recent_games)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"Error generating Steam card: {exc}", file=sys.stderr)
        sys.exit(1)
