"""Small helpers shared by the generator scripts."""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_light(hex_color: str) -> bool:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance > 0.6


def team_lookup(divisions_data: dict) -> dict:
    lookup = {}
    for div in divisions_data["divisions"]:
        for team in div["teams"]:
            lookup[team["id"]] = {
                "id": team["id"],
                "name": team["name"],
                "color": team["color"],
                "light_text": is_light(team["color"]),
                "logo": f"assets/logos/{team['id']}.png",
            }
    return lookup


def sync_assets(site_dir: Path) -> None:
    """Copy assets/ (team logos, etc.) into the generated site/ folder so it
    stays a single self-contained, portable directory."""
    dest = site_dir / "assets"
    if ASSETS_DIR.exists():
        shutil.copytree(ASSETS_DIR, dest, dirs_exist_ok=True)


# Categorical palette validated for the site's dark navy chart surface
# (data-viz skill's default order, first 7 slots -- worst adjacent CVD
# Delta E 8.4, worst adjacent normal-vision Delta E 19.3, all >=3:1 contrast
# against #131a2b). Assigned to bettors in a fixed order (their position in
# bettors.json), never by rank, so a color always means the same person
# week to week even as the leaderboard reshuffles.
CHART_PALETTE = [
    "#3987e5",  # blue
    "#d95926",  # orange
    "#199e70",  # aqua
    "#c98500",  # yellow
    "#d55181",  # magenta
    "#008300",  # green
    "#9085e9",  # violet
]


def bettor_colors(bettors_data: dict) -> dict:
    """bettor_id -> stable chart color, assigned by file order."""
    colors = {}
    for i, bettor in enumerate(bettors_data["bettors"]):
        colors[bettor["id"]] = CHART_PALETTE[i % len(CHART_PALETTE)]
    return colors
