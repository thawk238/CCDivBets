"""Render weekly analysis pages (data/weekly_facts/<season>-wkNN.json stats +
data/weekly_writeups/<season>-wkNN.json prose) into site/reports/week-NN.html.

Usage:
    python scripts/generate_week_report.py --all      # every week with a writeup (what deploys use)
    python scripts/generate_week_report.py            # latest week with a writeup
    python scripts/generate_week_report.py --week 3

Deploys rebuild the whole site/ folder from scratch each time (it's not
incremental), so --all is what the pipeline/Action should use -- otherwise
older weeks' report pages silently disappear from a fresh deploy.

Requires scripts/analyze_week.py to have been run for each week, and a
matching data/weekly_writeups/<season>-wkNN.json written (by hand -- that's
the actual commentary, not auto-generated).
"""

import argparse
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from _common import load_json, sync_assets

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
WEEKLY_FACTS_DIR = DATA_DIR / "weekly_facts"
WEEKLY_WRITEUPS_DIR = DATA_DIR / "weekly_writeups"
TEMPLATES_DIR = ROOT / "templates"
SITE_DIR = ROOT / "site"

POOL_NAME = "SUNDAY BEST DIVISIONAL POOL"


def find_facts_file(season: int, week: int | None) -> Path:
    if week is not None:
        path = WEEKLY_FACTS_DIR / f"{season}-wk{week:02d}.json"
        if not path.exists():
            raise SystemExit(f"No such weekly facts file: {path}. Run analyze_week.py first.")
        return path
    candidates = sorted(WEEKLY_FACTS_DIR.glob(f"{season}-wk*.json"))
    if not candidates:
        raise SystemExit("No weekly facts found. Run analyze_week.py first.")
    return candidates[-1]


def render_week(season: int, week: int, env: Environment) -> Path:
    facts_path = WEEKLY_FACTS_DIR / f"{season}-wk{week:02d}.json"
    if not facts_path.exists():
        raise SystemExit(f"No such weekly facts file: {facts_path}. Run analyze_week.py first.")
    facts = load_json(facts_path)

    writeup_path = WEEKLY_WRITEUPS_DIR / f"{season}-wk{week:02d}.json"
    if not writeup_path.exists():
        raise SystemExit(
            f"No write-up yet for week {week}: {writeup_path}\n"
            f"Write the commentary JSON (see an existing week for the shape) before generating."
        )
    writeup = load_json(writeup_path)

    fun_facts = [
        {"heading": f["heading"], "body_paragraphs": f["body"].split("\n\n")}
        for f in writeup["fun_facts"]
    ]

    template = env.get_template("week_report.html.j2")
    html = template.render(
        title=writeup["title"],
        subtitle=writeup["subtitle"],
        pool_name=POOL_NAME,
        week=week,
        intro_paragraphs=writeup["intro_paragraphs"],
        leaderboard=facts["leaderboard"],
        lock_status=facts["lock_status"],
        locks_holding=facts["locks_holding"],
        locks_broken=facts["locks_broken"],
        fun_facts=fun_facts,
        closing_paragraph=writeup["closing_paragraph"],
    )

    reports_dir = SITE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    out_path = reports_dir / f"week-{week:02d}.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--week", type=int, default=None)
    parser.add_argument("--all", action="store_true", help="Render every week that has a write-up")
    args = parser.parse_args()

    divisions_data = load_json(DATA_DIR / "divisions.json")
    season = args.season or divisions_data["season"]

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    sync_assets(SITE_DIR)
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)

    if args.all:
        writeup_files = sorted(WEEKLY_WRITEUPS_DIR.glob(f"{season}-wk*.json"))
        if not writeup_files:
            print("No weekly write-ups found -- nothing to render.")
            return
        for path in writeup_files:
            week = int(path.stem.split("-wk")[1])
            out_path = render_week(season, week, env)
            print(f"OK -- wrote {out_path}")
        return

    if args.week is not None:
        week = args.week
    else:
        week = load_json(find_facts_file(season, None))["week"]

    out_path = render_week(season, week, env)
    print(f"OK -- wrote {out_path}")


if __name__ == "__main__":
    main()
