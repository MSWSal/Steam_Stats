# Steam GitHub Status Card

Generates an SVG card showing your current Steam status (or what you're playing right
now) plus your recently-played games, and keeps it updated automatically via a GitHub
Action. Embed the SVG in any README (e.g. your GitHub profile README) to show live-ish
Steam activity.

## How it works

- `scripts/steam_card.py` calls the Steam Web API (`GetPlayerSummaries` for current
  status, `GetRecentlyPlayedGames` for the last 2 weeks) and renders `assets/steam-card.svg`.
- `.github/workflows/steam-stats.yml` runs that script every 30 minutes and commits the
  SVG back to the repo if it changed.
- Your README (or any other README) references the SVG, so it updates itself.

## Embedding it

```markdown
![Steam Status](https://raw.githubusercontent.com/<your-username>/<this-repo>/main/assets/steam-card.svg)
```
