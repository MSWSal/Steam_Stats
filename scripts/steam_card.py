#!/usr/bin/env python3
"""Generate an SVG card showing current Steam status and recent playtime."""
import html
import os
import sys
from datetime import datetime, timezone

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
    0: "#6e7681",   # offline — muted gray
    1: "#66c0f4",   # online — Steam blue
    2: "#f85149",   # busy — reserved "serious" red
    3: "#e3b341",   # away — reserved "warning" amber
    4: "#6e7681",   # snooze — muted gray
    5: "#66c0f4",   # looking to trade — Steam blue
    6: "#66c0f4",   # looking to play — Steam blue
}
IN_GAME_COLOR = "#3fb950"  # reserved "good" green
ACCENT = "#66c0f4"  # single hue used for magnitude (bar length), Steam brand blue


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
    avatar_url = summary.get("avatarfull", "")

    if in_game:
        headline = f"Playing {summary['gameextrainfo']}"
        dot_color = IN_GAME_COLOR
    else:
        headline = status_label
        dot_color = STATUS_COLORS.get(status_code, "#6e7681")

    width = 460
    avatar_size = 64
    header_h = 110
    bar_section_top = header_h + 48
    row_height = 34
    bottom_padding = 36

    rows = recent_games[:3]
    max_minutes = max((g.get("playtime_2weeks", 0) for g in rows), default=0)
    bar_track_w = width - 48

    bar_rows = []
    y = bar_section_top
    if rows:
        for game in rows:
            name = esc(game.get("name", "Unknown game"))
            minutes_2w = game.get("playtime_2weeks", 0)
            hours_2w = minutes_2w / 60
            frac = (minutes_2w / max_minutes) if max_minutes else 0
            fill_w = max(bar_track_w * frac, 6)
            bar_rows.append(f'''
      <text x="24" y="{y}" class="game">{name}</text>
      <text x="{width - 24}" y="{y}" text-anchor="end" class="hours">{hours_2w:.1f} hrs</text>
      <rect x="24" y="{y + 8}" width="{bar_track_w}" height="6" rx="3" class="track"/>
      <rect x="24" y="{y + 8}" width="{fill_w:.1f}" height="6" rx="3" fill="{ACCENT}"/>''')
            y += row_height
        content_bottom = y + 4
    else:
        bar_rows.append(
            f'<text x="24" y="{y}" class="game-muted">No games played in the last 2 weeks</text>'
        )
        content_bottom = y + 10

    height = content_bottom + bottom_padding
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    avatar_markup = ""
    if avatar_url:
        avatar_markup = f'''
    <clipPath id="avatarClip">
      <rect x="24" y="24" width="{avatar_size}" height="{avatar_size}" rx="8"/>
    </clipPath>
  </defs>
  <image href="{esc(avatar_url)}" x="24" y="24" width="{avatar_size}" height="{avatar_size}" clip-path="url(#avatarClip)"/>
  <rect x="24" y="24" width="{avatar_size}" height="{avatar_size}" rx="8" fill="none" stroke="#30363d" stroke-width="1"/>'''
    else:
        avatar_markup = "\n  </defs>"

    text_x = 24 + avatar_size + 16 if avatar_url else 24

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#121820"/>
      <stop offset="1" stop-color="#0d1117"/>
    </linearGradient>{avatar_markup}
  <rect class="card" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="url(#bg)" stroke="#30363d"/>
  <rect x="0.5" y="0.5" width="{width - 1}" height="3" rx="1.5" fill="{ACCENT}"/>

  <text x="{text_x}" y="40" class="title">{esc(persona)}</text>
  <circle cx="{text_x + 6}" cy="63" r="5" fill="{dot_color}"/>
  <circle cx="{text_x + 6}" cy="63" r="8" fill="{dot_color}" opacity="0.18"/>
  <text x="{text_x + 18}" y="67" class="headline">{esc(headline)}</text>

  <line x1="24" y1="{header_h}" x2="{width - 24}" y2="{header_h}" stroke="#21262d" stroke-width="1"/>
  <text x="24" y="{header_h + 20}" class="section">Recently Played (last 2 weeks)</text>
  {''.join(bar_rows)}

  <text x="{width - 24}" y="{height - 16}" text-anchor="end" class="footer">Updated {updated}</text>

  <style>
    .title {{ font: 600 16px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #e6edf3; }}
    .headline {{ font: 500 13px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #c9d1d9; }}
    .section {{ font: 600 11px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #8b949e; letter-spacing: 0.06em; text-transform: uppercase; }}
    .game {{ font: 500 12px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #c9d1d9; }}
    .game-muted {{ font: 400 12px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #6e7681; }}
    .hours {{ font: 400 11px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #8b949e; }}
    .footer {{ font: 400 10px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #484f58; }}
    .track {{ fill: #21262d; }}
  </style>
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
