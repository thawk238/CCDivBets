"""Render the one-time preseason scouting report (data/preseason_writeup.json
+ data/preseason_facts.json) into site/preseason.html.

Picks are locked before the season, so unlike generate_site.py this has no
"latest week" concept -- it only needs re-running if data/picks.json,
data/preseason_facts.json (via scripts/analyze_picks.py), or the write-up
prose in data/preseason_writeup.json change.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from _common import load_json, sync_assets, team_lookup

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TEMPLATES_DIR = ROOT / "templates"
SITE_DIR = ROOT / "site"

POOL_NAME = "SUNDAY BEST DIVISIONAL POOL"
SLOT_LABELS = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th"}


def main():
    divisions_data = load_json(DATA_DIR / "divisions.json")
    bettors_data = load_json(DATA_DIR / "bettors.json")
    facts = load_json(DATA_DIR / "preseason_facts.json")
    writeup = load_json(DATA_DIR / "preseason_writeup.json")

    teams = team_lookup(divisions_data)

    locked_slots = [
        {
            "team": teams[slot["team"]],
            "slot_label": SLOT_LABELS[slot["slot"]],
            "division_name": slot["division_name"],
        }
        for slot in facts["league_wide"]["locked_slots"]
    ]

    fun_facts = [
        {"heading": f["heading"], "body_paragraphs": f["body"].split("\n\n")}
        for f in writeup["fun_facts"]
    ]

    bettor_profiles = []
    for bettor in bettors_data["bettors"]:
        bid = bettor["id"]
        bettor_profiles.append(
            {
                "name": bettor["name"],
                "body": writeup["bettor_profiles"][bid],
                "lone_wolf_count": len(facts["bettors"][bid]["lone_wolf_picks"]),
            }
        )
    bettor_profiles.sort(key=lambda b: -b["lone_wolf_count"])

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    template = env.get_template("preseason.html.j2")
    html = template.render(
        title=writeup["title"],
        subtitle=writeup["subtitle"],
        pool_name=POOL_NAME,
        intro_paragraphs=writeup["intro_paragraphs"],
        locked_slots=locked_slots,
        fun_facts=fun_facts,
        bettor_profiles=bettor_profiles,
        closing_paragraph=writeup["closing_paragraph"],
    )

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    sync_assets(SITE_DIR)
    out_path = SITE_DIR / "preseason.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"OK -- wrote {out_path}")


if __name__ == "__main__":
    main()
