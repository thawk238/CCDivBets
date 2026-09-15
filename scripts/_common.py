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
