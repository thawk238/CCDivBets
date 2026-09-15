"""One-time download of real team logos into assets/logos/<TEAM_ID>.png.

Source: ESPN's public team-logo CDN (a.espncdn.com/i/teamlogos/nfl/500/<abbr>.png),
which happens to use the same lowercase abbreviations as data/divisions.json's
team ids for all 32 NFL teams (verified before writing this script).

Logos never change mid-season, so this doesn't belong in the weekly
pipeline -- run it once, or again only if a team's logo needs refreshing.
"""

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
ASSETS_DIR = ROOT / "assets" / "logos"
LOGO_URL = "https://a.espncdn.com/i/teamlogos/nfl/500/{abbr}.png"


def main():
    with open(DATA_DIR / "divisions.json", encoding="utf-8") as f:
        divisions_data = json.load(f)

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    team_ids = [t["id"] for d in divisions_data["divisions"] for t in d["teams"]]
    for team_id in team_ids:
        out_path = ASSETS_DIR / f"{team_id}.png"
        url = LOGO_URL.format(abbr=team_id.lower())
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(resp.content)
        print(f"OK  {team_id:<4} <- {url}  ({len(resp.content)} bytes)")

    print(f"\nSaved {len(team_ids)} logos to {ASSETS_DIR}")


if __name__ == "__main__":
    main()
