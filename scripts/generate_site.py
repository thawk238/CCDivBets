"""Render data/*.json + data/scores/*.json into a single static site/index.html
using the "Blitz" template (templates/index.html.j2).

Reads the latest standings snapshot (for actual order + records) and the
matching data/scores/<season>-wkNN.json (for computed points -- run
compute_scores.py first if it's missing). Score history pulls every
data/scores/*.json file present, so the page always shows the full season
so far.
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from _common import bettor_colors, load_json, sync_assets, team_lookup

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STANDINGS_DIR = DATA_DIR / "standings"
SCORES_DIR = DATA_DIR / "scores"
TEMPLATES_DIR = ROOT / "templates"
SITE_DIR = ROOT / "site"

POOL_NAME_LINE1 = "SUNDAY BEST"
POOL_NAME_LINE2 = "DIVISIONAL POOL"


def find_latest(dir_path: Path, season: int | None) -> Path:
    candidates = sorted(
        p for p in dir_path.glob("*.json") if not p.name.endswith(".pending-review.json")
    )
    if season is not None:
        candidates = [p for p in candidates if p.name.startswith(f"{season}-wk")]
    if not candidates:
        raise SystemExit(f"No snapshot files found in {dir_path}")
    return candidates[-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=None)
    args = parser.parse_args()

    divisions_data = load_json(DATA_DIR / "divisions.json")
    bettors_data = load_json(DATA_DIR / "bettors.json")
    picks_data = load_json(DATA_DIR / "picks.json")
    tiebreaker_data = load_json(DATA_DIR / "tiebreaker.json")

    season = args.season or divisions_data["season"]
    teams = team_lookup(divisions_data)

    standings_path = find_latest(STANDINGS_DIR, season)
    standings = load_json(standings_path)
    week = standings["week"]

    scores_path = SCORES_DIR / f"{season}-wk{week:02d}.json"
    if not scores_path.exists():
        raise SystemExit(
            f"No scores file for week {week} ({scores_path}). "
            f"Run: python scripts/compute_scores.py"
        )
    scores = load_json(scores_path)

    # ---- Leaderboard ----
    leaderboard = []
    lb_order = scores["leaderboard"]
    for i, bid in enumerate(lb_order):
        b = scores["bettors"][bid]
        rank = i + 1
        tied = False
        if i > 0:
            prev = scores["bettors"][lb_order[i - 1]]
            tied = (
                b["total"] == prev["total"]
                and b["perfect_divisions_count"] == prev["perfect_divisions_count"]
                and b["top2_bonus_count"] == prev["top2_bonus_count"]
                and b["bottom2_bonus_count"] == prev["bottom2_bonus_count"]
                and b["total_exact_hits"] == prev["total_exact_hits"]
            )
            if tied:
                rank = leaderboard[-1]["rank"]
        leaderboard.append(
            {
                "rank": rank,
                "name": b["name"],
                "total": b["total"],
                "perfect_divisions_count": b["perfect_divisions_count"],
                "top2_bonus_count": b["top2_bonus_count"],
                "bottom2_bonus_count": b["bottom2_bonus_count"],
                "total_exact_hits": b["total_exact_hits"],
                "tied": tied,
            }
        )

    # ---- Standings by division (actual order + records) ----
    standings_by_division = {}
    for div_id, team_rows in standings["divisions"].items():
        standings_by_division[div_id] = [
            {**teams[row["team_id"]], "wins": row["wins"], "losses": row["losses"], "ties": row["ties"]}
            for row in team_rows
        ]

    # ---- Division breakdown (per division, per bettor) ----
    division_breakdown = {div["id"]: [] for div in divisions_data["divisions"]}
    for bid in lb_order:  # keep leaderboard order within each division too
        b = scores["bettors"][bid]
        for div_id, d in b["per_division"].items():
            division_breakdown[div_id].append(
                {
                    "name": b["name"],
                    "predicted_teams": [teams[t] for t in d["predicted"]],
                    "exact_flags": d["exact_flags"],
                    "perfect": d["perfect"],
                    "top2_bonus": d["top2_bonus"],
                    "bottom2_bonus": d["bottom2_bonus"],
                    "division_total": d["division_total"],
                }
            )

    # ---- Score history across all weeks scored so far ----
    all_score_files = sorted(
        p for p in SCORES_DIR.glob(f"{season}-wk*.json")
    )
    history_weeks = []
    by_bettor_week = {b["id"]: {} for b in bettors_data["bettors"]}
    for p in all_score_files:
        wk_scores = load_json(p)
        wk = wk_scores["week"]
        history_weeks.append(wk)
        for bid, b in wk_scores["bettors"].items():
            by_bettor_week[bid][wk] = b["total"]

    colors = bettor_colors(bettors_data)
    history = []
    chart_series = []
    for bettor in bettors_data["bettors"]:
        by_week = by_bettor_week[bettor["id"]]
        history.append({"name": bettor["name"], "by_week": by_week, "color": colors[bettor["id"]]})
        chart_series.append(
            {
                "name": bettor["name"],
                "color": colors[bettor["id"]],
                "points": [by_week[w] for w in history_weeks],
            }
        )

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    template = env.get_template("index.html.j2")

    html = template.render(
        pool_name=f"{POOL_NAME_LINE1} {POOL_NAME_LINE2}",
        pool_name_line1=POOL_NAME_LINE1,
        pool_name_line2=POOL_NAME_LINE2,
        season=season,
        current_week=week,
        generated_at=datetime.now(timezone.utc).strftime("%b %d, %Y %H:%M UTC"),
        leaderboard=leaderboard,
        divisions=divisions_data["divisions"],
        standings_by_division=standings_by_division,
        division_breakdown=division_breakdown,
        history_weeks=history_weeks,
        history=history,
        chart_series=chart_series,
        tiebreaker=tiebreaker_data,
        unresolved_ties=scores.get("unresolved_ties", []),
        standings_source_url=standings["source_url"],
    )

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    sync_assets(SITE_DIR)
    out_path = SITE_DIR / "index.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"OK -- wrote {out_path}")


if __name__ == "__main__":
    main()
