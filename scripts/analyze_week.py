"""Compute fun-facts stats for one week's results, for the weekly analysis
write-up (separate from the preseason one -- this looks at how actual
standings are shaping up against everyone's locked picks).

Usage:
    python scripts/analyze_week.py            # latest scored week
    python scripts/analyze_week.py --week 3

Writes data/weekly_facts/<season>-wkNN.json:
  - leaderboard snapshot + point deltas vs the previous scored week (if any)
  - closest/widest gaps between consecutive leaderboard spots
  - "preseason hopes tracker": how many of each bettor's 8 division-winner
    picks are currently sitting in first place for real
  - which of the preseason's unanimous "locks" are holding up vs. already
    broken by the real standings
"""

import argparse
import json
from pathlib import Path

from _common import load_json

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SCORES_DIR = DATA_DIR / "scores"
STANDINGS_DIR = DATA_DIR / "standings"
WEEKLY_FACTS_DIR = DATA_DIR / "weekly_facts"


def find_scores_file(season: int, week: int | None) -> Path:
    if week is not None:
        path = SCORES_DIR / f"{season}-wk{week:02d}.json"
        if not path.exists():
            raise SystemExit(f"No such scores file: {path}")
        return path
    candidates = sorted(SCORES_DIR.glob(f"{season}-wk*.json"))
    if not candidates:
        raise SystemExit("No scored weeks found. Run compute_scores.py first.")
    return candidates[-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--week", type=int, default=None)
    args = parser.parse_args()

    divisions_data = load_json(DATA_DIR / "divisions.json")
    bettors_data = load_json(DATA_DIR / "bettors.json")
    preseason_facts = load_json(DATA_DIR / "preseason_facts.json")

    season = args.season or divisions_data["season"]
    scores_path = find_scores_file(season, args.week)
    scores = load_json(scores_path)
    week = scores["week"]

    standings_path = STANDINGS_DIR / f"{season}-wk{week:02d}.json"
    standings = load_json(standings_path)

    team_name = {t["id"]: t["name"] for d in divisions_data["divisions"] for t in d["teams"]}

    # ---- leaderboard snapshot + deltas vs previous scored week ----
    prev_candidates = sorted(
        p for p in SCORES_DIR.glob(f"{season}-wk*.json") if p != scores_path
    )
    prev_scores = None
    if prev_candidates:
        # the previous week is the highest-numbered one below this week
        earlier = [p for p in prev_candidates if load_json(p)["week"] < week]
        if earlier:
            prev_scores = load_json(sorted(earlier, key=lambda p: load_json(p)["week"])[-1])

    leaderboard = []
    for i, bid in enumerate(scores["leaderboard"]):
        b = scores["bettors"][bid]
        delta = None
        if prev_scores and bid in prev_scores["bettors"]:
            delta = b["total"] - prev_scores["bettors"][bid]["total"]
        leaderboard.append({"bettor_id": bid, "name": b["name"], "rank": i + 1, "total": b["total"], "delta": delta})

    gaps = []
    for i in range(len(leaderboard) - 1):
        gaps.append(
            {
                "between": [leaderboard[i]["name"], leaderboard[i + 1]["name"]],
                "gap": leaderboard[i]["total"] - leaderboard[i + 1]["total"],
            }
        )

    # ---- preseason hopes tracker: how many division-winner picks are currently #1 ----
    actual_first_place = {
        div_id: rows[0]["team_id"] for div_id, rows in standings["divisions"].items()
    }

    hopes_tracker = {}
    for bettor in bettors_data["bettors"]:
        bid = bettor["id"]
        top_picks = preseason_facts["bettors"][bid]["top_picks"]
        correct, wrong = [], []
        for pick in top_picks:
            actual_team = actual_first_place[pick["division"]]
            entry = {
                "division_name": pick["division_name"],
                "picked_team": pick["team_name"],
                "actual_team": team_name[actual_team],
            }
            (correct if actual_team == pick["team"] else wrong).append(entry)
        hopes_tracker[bid] = {
            "name": bettor["name"],
            "correct_count": len(correct),
            "total": len(top_picks),
            "correct": correct,
            "wrong": wrong,
        }

    # ---- preseason unanimous locks: still holding vs already broken ----
    lock_status = []
    for slot in preseason_facts["league_wide"]["locked_slots"]:
        actual_team = standings["divisions"][slot["division"]][slot["slot"] - 1]["team_id"]
        lock_status.append(
            {
                "division_name": slot["division_name"],
                "slot": slot["slot"],
                "predicted_team": slot["team_name"],
                "holding": actual_team == slot["team"],
                "actual_team_name": team_name[actual_team],
            }
        )

    output = {
        "season": season,
        "week": week,
        "has_previous_week": prev_scores is not None,
        "leaderboard": leaderboard,
        "gaps": gaps,
        "closest_gap": min(gaps, key=lambda g: g["gap"]) if gaps else None,
        "widest_gap": max(gaps, key=lambda g: g["gap"]) if gaps else None,
        "hopes_tracker": hopes_tracker,
        "lock_status": lock_status,
        "locks_holding": sum(1 for s in lock_status if s["holding"]),
        "locks_broken": sum(1 for s in lock_status if not s["holding"]),
    }

    WEEKLY_FACTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = WEEKLY_FACTS_DIR / f"{season}-wk{week:02d}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"OK -- wrote {out_path}")


if __name__ == "__main__":
    main()
