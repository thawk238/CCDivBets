"""Render site/reports.html -- an index linking to the preseason scouting
report and every week's analysis write-up found in data/weekly_writeups/.

Re-run this any time a new data/weekly_writeups/<season>-wkNN.json is added
(after generate_week_report.py has rendered that week's page).
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from _common import load_json, sync_assets

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
WEEKLY_WRITEUPS_DIR = DATA_DIR / "weekly_writeups"
TEMPLATES_DIR = ROOT / "templates"
SITE_DIR = ROOT / "site"

POOL_NAME = "SUNDAY BEST DIVISIONAL POOL"


def main():
    preseason_writeup = load_json(DATA_DIR / "preseason_writeup.json")

    reports = [
        {
            "title": preseason_writeup["title"],
            "subtitle": preseason_writeup["subtitle"],
            "href": "preseason.html",
            "featured": True,
        }
    ]

    week_files = sorted(WEEKLY_WRITEUPS_DIR.glob("*.json"), reverse=True)
    for path in week_files:
        writeup = load_json(path)
        week_num = int(path.stem.split("-wk")[1])
        reports.append(
            {
                "title": writeup["title"],
                "subtitle": writeup["subtitle"],
                "href": f"reports/week-{week_num:02d}.html",
                "featured": False,
            }
        )

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    template = env.get_template("reports_hub.html.j2")
    html = template.render(pool_name=POOL_NAME, reports=reports)

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    sync_assets(SITE_DIR)
    out_path = SITE_DIR / "reports.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"OK -- wrote {out_path}")


if __name__ == "__main__":
    main()
