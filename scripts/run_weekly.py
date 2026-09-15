"""Single entrypoint for the Tuesday-morning update: scrape -> compute ->
analyze -> rebuild the whole site/ folder.

Usage:
    python scripts/run_weekly.py

Stops after scraping if Yahoo's standings fail validation (see
scrape_standings.py) rather than computing/publishing against bad or
partial data.

Rebuilds site/ from scratch every run -- index.html, preseason.html,
reports.html, and every reports/week-NN.html that already has a write-up.
That's required, not just convenient: a deploy (GitHub Pages via the
Action, or copying site/ anywhere) replaces the whole folder each time, so
any page this script doesn't regenerate would vanish from a fresh deploy
even though its source data is still sitting in data/.

This does NOT write or publish THIS week's analysis report -- the fun-facts
stats are computed (data/weekly_facts/<season>-wkNN.json) but the actual
commentary in data/weekly_writeups/<season>-wkNN.json has to be written by
hand (or by asking Claude, which is the point) before it'll appear. Until
then, this run simply republishes the reports that already exist.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
DATA_DIR = ROOT / "data"


def run(script_name: str, *args: str) -> None:
    cmd = [sys.executable, str(SCRIPTS / script_name), *args]
    print(f"\n=== {script_name} {' '.join(args)} ===", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n{script_name} failed (exit {result.returncode}) -- stopping.", file=sys.stderr)
        sys.exit(result.returncode)


def latest_week_facts() -> dict | None:
    candidates = sorted((DATA_DIR / "weekly_facts").glob("*.json"))
    if not candidates:
        return None
    with open(candidates[-1], encoding="utf-8") as f:
        return json.load(f)


def main():
    run("scrape_standings.py")
    run("compute_scores.py")
    run("analyze_week.py")
    run("generate_site.py")
    run("generate_preseason.py")
    run("generate_week_report.py", "--all")
    run("generate_reports_hub.py")

    print("\nDone. site/ is fully rebuilt (leaderboard, preseason report, and every week's analysis that has a write-up).")

    facts = latest_week_facts()
    if facts:
        season, week = facts["season"], facts["week"]
        writeup_path = DATA_DIR / "weekly_writeups" / f"{season}-wk{week:02d}.json"
        if not writeup_path.exists():
            print(
                f"\nWeek {week}'s commentary hasn't been written yet -- "
                f"data/weekly_facts/{season}-wk{week:02d}.json has the fresh stats. "
                f"Write {writeup_path.relative_to(ROOT)}, then run this again (or just "
                f"generate_week_report.py --all + generate_reports_hub.py) to add it in."
            )


if __name__ == "__main__":
    main()
