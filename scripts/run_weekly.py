"""Single entrypoint for the Tuesday-morning update: scrape -> compute ->
generate -> analyze.

Usage:
    python scripts/run_weekly.py

Stops after scraping if Yahoo's standings fail validation (see
scrape_standings.py) rather than computing/publishing against bad or
partial data.

This does NOT write or publish that week's analysis report -- the fun-facts
stats are computed (data/weekly_facts/<season>-wkNN.json) but the actual
commentary in data/weekly_writeups/<season>-wkNN.json has to be written by
hand (or by asking Claude, which is the point), then rendered with:
    python scripts/generate_week_report.py
    python scripts/generate_reports_hub.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


def run(script_name: str, *args: str) -> None:
    cmd = [sys.executable, str(SCRIPTS / script_name), *args]
    print(f"\n=== {script_name} {' '.join(args)} ===", flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n{script_name} failed (exit {result.returncode}) -- stopping.", file=sys.stderr)
        sys.exit(result.returncode)


def main():
    run("scrape_standings.py")
    run("compute_scores.py")
    run("generate_site.py")
    run("analyze_week.py")
    print(
        "\nDone. site/index.html is updated.\n"
        "Weekly facts are ready in data/weekly_facts/ -- write this week's "
        "commentary to data/weekly_writeups/<season>-wkNN.json, then run:\n"
        "  python scripts/generate_week_report.py\n"
        "  python scripts/generate_reports_hub.py"
    )


if __name__ == "__main__":
    main()
