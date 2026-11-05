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
OWNED_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"

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


def fetch_owned_games():
    resp = requests.get(
        OWNED_URL,
        params={
            "key": API_KEY,
            "steamid": STEAM_ID,
            "include_appinfo": 1,
            "include_played_free_games": 1,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()["response"]
    return data.get("game_count", 0), data.get("games", [])


def esc(text):
    return html.escape(str(text), quote=True)


def bar_rows_block(games, key, width, start_y, row_height, limit, empty_message):
    rows = games[:limit]
    bar_track_w = width - 48
    max_val = max((g.get(key, 0) for g in rows), default=0)

    blocks = []
    y = start_y
    if rows:
        for game in rows:
            name = esc(game.get("name", "Unknown game"))
            minutes = game.get(key, 0)
            hours = minutes / 60
            frac = (minutes / max_val) if max_val else 0
            fill_w = max(bar_track_w * frac, 6)
            blocks.append(f'''
      <text x="24" y="{y}" class="game">{name}</text>
      <text x="{width - 24}" y="{y}" text-anchor="end" class="hours">{hours:,.1f} hrs</text>
      <rect x="24" y="{y + 8}" width="{bar_track_w}" height="6" rx="3" class="track"/>
      <rect x="24" y="{y + 8}" width="{fill_w:.1f}" height="6" rx="3" fill="{ACCENT}"/>''')
            y += row_height
        bottom = y + 4
    else:
        blocks.append(f'<text x="24" y="{y}" class="game-muted">{esc(empty_message)}</text>')
        bottom = y + 10
    return "".join(blocks), bottom


def render_svg(summary, recent_games, game_count, owned_games):
    in_game = "gameextrainfo" in summary
    status_code = summary.get("personastate", 0)
    status_label = STATUS_NAMES.get(status_code, "Unknown")
    persona = summary.get("personaname", "Steam User")
    avatar_url = summary.get("avatarfull", "")
    profile_url = summary.get("profileurl", "")
    country = summary.get("loccountrycode", "")

    if in_game:
        headline = f"Playing {summary['gameextrainfo']}"
        dot_color = IN_GAME_COLOR
    else:
        headline = status_label
        dot_color = STATUS_COLORS.get(status_code, "#6e7681")

    width = 480
    avatar_size = 64
    header_h = 118
    row_height = 34

    text_x = 24 + avatar_size + 16 if avatar_url else 24
    subtitle_parts = [p for p in [profile_url.replace("https://", ""), country] if p]
    subtitle = "  ·  ".join(subtitle_parts)

    # Stat tiles: games owned / lifetime hours
    total_minutes = sum(g.get("playtime_forever", 0) for g in owned_games)
    total_hours = total_minutes / 60
    stats_top = header_h + 14
    stats_bottom = stats_top + 46

    # Top games all-time (by playtime_forever)
    top_games_sorted = sorted(owned_games, key=lambda g: g.get("playtime_forever", 0), reverse=True)
    top_section_label_y = stats_bottom + 24
    top_bars, top_bottom = bar_rows_block(
        top_games_sorted, "playtime_forever", width, top_section_label_y + 18, row_height, 5,
        "No playtime data available",
    )

    # Recently played (last 2 weeks)
    recent_section_label_y = top_bottom + 20
    recent_bars, recent_bottom = bar_rows_block(
        recent_games, "playtime_2weeks", width, recent_section_label_y + 18, row_height, 3,
        "No games played in the last 2 weeks",
    )

    height = recent_bottom + 36
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

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#121820"/>
      <stop offset="1" stop-color="#0d1117"/>
    </linearGradient>{avatar_markup}
  <rect class="card" x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" fill="url(#bg)" stroke="#30363d"/>
  <rect x="0.5" y="0.5" width="{width - 1}" height="3" rx="1.5" fill="{ACCENT}"/>

  <text x="{text_x}" y="40" class="title">{esc(persona)}</text>
  <text x="{text_x}" y="56" class="subtitle">{esc(subtitle)}</text>
  <circle cx="{text_x + 6}" cy="78" r="5" fill="{dot_color}"/>
  <circle cx="{text_x + 6}" cy="78" r="8" fill="{dot_color}" opacity="0.18"/>
  <text x="{text_x + 18}" y="82" class="headline">{esc(headline)}</text>

  <line x1="24" y1="{header_h}" x2="{width - 24}" y2="{header_h}" stroke="#21262d" stroke-width="1"/>

  <text x="24" y="{stats_top + 16}" class="stat-num">{game_count:,}</text>
  <text x="24" y="{stats_top + 32}" class="stat-label">Games Owned</text>
  <text x="{width / 2 + 12:.0f}" y="{stats_top + 16}" class="stat-num">{total_hours:,.0f}</text>
  <text x="{width / 2 + 12:.0f}" y="{stats_top + 32}" class="stat-label">Lifetime Hours</text>
  <line x1="{width / 2:.0f}" y1="{stats_top - 4}" x2="{width / 2:.0f}" y2="{stats_bottom - 10}" stroke="#21262d" stroke-width="1"/>

  <line x1="24" y1="{stats_bottom}" x2="{width - 24}" y2="{stats_bottom}" stroke="#21262d" stroke-width="1"/>
  <text x="24" y="{top_section_label_y}" class="section">Top Games (All Time)</text>
  {top_bars}

  <line x1="24" y1="{top_bottom + 8}" x2="{width - 24}" y2="{top_bottom + 8}" stroke="#21262d" stroke-width="1"/>
  <text x="24" y="{recent_section_label_y}" class="section">Recently Played (Last 2 Weeks)</text>
  {recent_bars}

  <text x="{width - 24}" y="{height - 16}" text-anchor="end" class="footer">Updated {updated}</text>

  <style>
    .title {{ font: 600 16px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #e6edf3; }}
    .subtitle {{ font: 400 11px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #6e7681; }}
    .headline {{ font: 500 13px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #c9d1d9; }}
    .section {{ font: 600 11px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #8b949e; letter-spacing: 0.06em; text-transform: uppercase; }}
    .game {{ font: 500 12px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #c9d1d9; }}
    .game-muted {{ font: 400 12px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #6e7681; }}
    .hours {{ font: 400 11px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #8b949e; }}
    .footer {{ font: 400 10px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #484f58; }}
    .track {{ fill: #21262d; }}
    .stat-num {{ font: 700 20px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #e6edf3; }}
    .stat-label {{ font: 600 10px -apple-system, Segoe UI, Helvetica, Arial, sans-serif; fill: #8b949e; letter-spacing: 0.05em; text-transform: uppercase; }}
  </style>
</svg>'''
    return svg


def main():
    summary = fetch_summary()
    recent_games = fetch_recent()
    game_count, owned_games = fetch_owned_games()
    svg = render_svg(summary, recent_games, game_count, owned_games)

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
