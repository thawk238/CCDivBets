"""Fetch NFL division standings from Yahoo Sports and write a dated snapshot.

Yahoo embeds the standings as schema.org JSON-LD (one ItemList per division,
positions already in finish order) inside a <script type="application/ld+json">
tag on https://sports.yahoo.com/nfl/standings/. That's far more stable than
scraping the rendered page markup, so this script reads that block rather
than parsing visible HTML.

Safety net: before writing anything, the parsed result is validated against
data/divisions.json (exactly 8 divisions, each with exactly 4 known teams,
no duplicates). If validation fails, nothing live is overwritten -- a
"<week>.pending-review.json" file is written instead and the script exits
non-zero, so a broken/blocked scrape can never silently go out on a Tuesday.
"""

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STANDINGS_DIR = DATA_DIR / "standings"
STANDINGS_URL = "https://sports.yahoo.com/nfl/standings/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# 2026 season opener (first Thursday night game, Sept 10 2026). Used only
# to label the snapshot with a week number when --week isn't given.
SEASON_START = date(2026, 9, 10)


def current_week(today: date | None = None) -> int:
    today = today or date.today()
    days_in = (today - SEASON_START).days
    return max(1, (days_in // 7) + 1)


def load_divisions() -> dict:
    with open(DATA_DIR / "divisions.json", encoding="utf-8") as f:
        return json.load(f)


def build_city_lookup(divisions_data: dict) -> dict:
    """yahoo_city -> (division_id, team_id)"""
    lookup = {}
    for div in divisions_data["divisions"]:
        for team in div["teams"]:
            lookup[team["yahoo_city"]] = (div["id"], team["id"])
    return lookup


def normalize_division_name(yahoo_list_name: str) -> str:
    # "NFC South Standings — 2026" -> "NFC South"
    name = re.split(r"\s+Standings\b", yahoo_list_name)[0].strip()
    return name


def name_to_id(name: str) -> str:
    # "NFC South" -> "nfc-south"
    return name.lower().replace(" ", "-")


def fetch_ld_json(html: str) -> dict:
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    )
    for block in blocks:
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "@graph" in data:
            return data
    raise ValueError("No parseable ld+json @graph block found on the standings page")


def extract_property(item: dict, name: str):
    for prop in item.get("additionalProperty", []):
        if prop.get("name") == name:
            return prop.get("value")
    return None


def parse_standings(html: str, divisions_data: dict) -> dict:
    ld = fetch_ld_json(html)
    city_lookup = build_city_lookup(divisions_data)

    result = {}
    for node in ld.get("@graph", []):
        if node.get("@type") != "ItemList":
            continue
        div_name = normalize_division_name(node.get("name", ""))
        div_id = name_to_id(div_name)

        teams = []
        for entry in sorted(node["itemListElement"], key=lambda e: e["position"]):
            item = entry["item"]
            city = item.get("name")
            match = city_lookup.get(city)
            teams.append(
                {
                    "yahoo_city": city,
                    "team_id": match[1] if match else None,
                    "wins": extract_property(item, "W"),
                    "losses": extract_property(item, "L"),
                    "ties": extract_property(item, "T"),
                    "pct": extract_property(item, "PCT"),
                    "pf": extract_property(item, "PF"),
                    "pa": extract_property(item, "PA"),
                }
            )
        result[div_id] = teams
    return result


def validate(parsed: dict, divisions_data: dict) -> list[str]:
    """Returns a list of validation error strings (empty = valid)."""
    errors = []
    expected_divisions = {d["id"] for d in divisions_data["divisions"]}
    expected_teams = {
        d["id"]: {t["id"] for t in d["teams"]} for d in divisions_data["divisions"]
    }

    found_divisions = set(parsed.keys())
    missing = expected_divisions - found_divisions
    extra = found_divisions - expected_divisions
    if missing:
        errors.append(f"missing divisions: {sorted(missing)}")
    if extra:
        errors.append(f"unrecognized divisions: {sorted(extra)}")

    for div_id, teams in parsed.items():
        if div_id not in expected_teams:
            continue
        if len(teams) != 4:
            errors.append(f"{div_id}: expected 4 teams, got {len(teams)}")

        team_ids = [t["team_id"] for t in teams]
        if None in team_ids:
            unmatched = [t["yahoo_city"] for t in teams if t["team_id"] is None]
            errors.append(f"{div_id}: unmatched team name(s) {unmatched}")
            continue

        if len(set(team_ids)) != len(team_ids):
            errors.append(f"{div_id}: duplicate teams {team_ids}")

        if set(team_ids) != expected_teams[div_id]:
            errors.append(
                f"{div_id}: team set {sorted(team_ids)} != expected "
                f"{sorted(expected_teams[div_id])}"
            )

    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--week", type=int, default=None, help="Week number label (default: auto)"
    )
    parser.add_argument(
        "--season", type=int, default=None, help="Season year label (default: from divisions.json)"
    )
    args = parser.parse_args()

    divisions_data = load_divisions()
    season = args.season or divisions_data["season"]
    week = args.week or current_week()

    print(f"Fetching {STANDINGS_URL} ...")
    resp = requests.get(STANDINGS_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()

    parsed = parse_standings(resp.text, divisions_data)
    errors = validate(parsed, divisions_data)

    STANDINGS_DIR.mkdir(parents=True, exist_ok=True)
    week_label = f"{season}-wk{week:02d}"

    snapshot = {
        "season": season,
        "week": week,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "source_url": STANDINGS_URL,
        "divisions": parsed,
    }

    if errors:
        out_path = STANDINGS_DIR / f"{week_label}.pending-review.json"
        snapshot["validation_errors"] = errors
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)
        print("VALIDATION FAILED -- nothing published. Details:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        print(f"Raw parse written for review: {out_path}", file=sys.stderr)
        sys.exit(1)

    out_path = STANDINGS_DIR / f"{week_label}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)
    print(f"OK -- wrote {out_path}")


if __name__ == "__main__":
    main()
