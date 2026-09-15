"""Score every bettor's locked picks against a weekly standings snapshot.

Scoring rules (per division, per bettor):
  - Exact position (1-4) correct: +3 per team
  - Perfect division (all 4 exact): +8 bonus
  - Top-2 in exact order (positions 1 & 2 both exact): +3 bonus
  - Bottom-2 in exact order (positions 3 & 4 both exact): +2 bonus
  Division max: 4x3 + 8+3+2 = 25. Season max (8 divisions): 200.

Also tallies, per bettor, the automatic tiebreaker stats in official
priority order: perfect-division count -> top-2-bonus count ->
bottom-2-bonus count -> total exact hits (out of 32). Tiebreaker #5 (a
season-long point-total guess) lives in data/tiebreaker.json and is only
meaningful if a tie survives all four of the above -- this script flags
that case but does not resolve it, since the guess data is currently unset.

Output is derived data: never hand-edit files in data/scores/.
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
STANDINGS_DIR = DATA_DIR / "standings"
SCORES_DIR = DATA_DIR / "scores"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_latest_standings(season: int | None) -> Path:
    candidates = sorted(
        p for p in STANDINGS_DIR.glob("*.json") if not p.name.endswith(".pending-review.json")
    )
    if season is not None:
        candidates = [p for p in candidates if p.name.startswith(f"{season}-wk")]
    if not candidates:
        raise SystemExit("No standings snapshots found. Run scripts/scrape_standings.py first.")
    return candidates[-1]


def score_division(predicted: list[str], actual: list[str]) -> dict:
    exact_flags = [p == a for p, a in zip(predicted, actual)]
    exact_count = sum(exact_flags)
    perfect = exact_count == 4
    top2_bonus = exact_flags[0] and exact_flags[1]
    bottom2_bonus = exact_flags[2] and exact_flags[3]

    total = exact_count * 3 + (8 if perfect else 0) + (3 if top2_bonus else 0) + (2 if bottom2_bonus else 0)

    return {
        "predicted": predicted,
        "actual": actual,
        "exact_flags": exact_flags,
        "exact_count": exact_count,
        "perfect": perfect,
        "top2_bonus": top2_bonus,
        "bottom2_bonus": bottom2_bonus,
        "division_total": total,
    }


def rank_key(bettor_result: dict) -> tuple:
    # Higher is better for every field; Python sorts ascending, so negate.
    return (
        -bettor_result["total"],
        -bettor_result["perfect_divisions_count"],
        -bettor_result["top2_bonus_count"],
        -bettor_result["bottom2_bonus_count"],
        -bettor_result["total_exact_hits"],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--week", type=int, default=None, help="Use a specific week's snapshot instead of the latest")
    args = parser.parse_args()

    divisions_data = load_json(DATA_DIR / "divisions.json")
    bettors_data = load_json(DATA_DIR / "bettors.json")
    picks_data = load_json(DATA_DIR / "picks.json")

    season = args.season or divisions_data["season"]

    if args.week is not None:
        standings_path = STANDINGS_DIR / f"{season}-wk{args.week:02d}.json"
        if not standings_path.exists():
            raise SystemExit(f"No such standings snapshot: {standings_path}")
    else:
        standings_path = find_latest_standings(season)

    standings = load_json(standings_path)
    division_ids = [d["id"] for d in divisions_data["divisions"]]

    bettor_results = {}
    for bettor in bettors_data["bettors"]:
        bid = bettor["id"]
        predicted_by_division = picks_data["picks"][bid]

        per_division = {}
        for div_id in division_ids:
            predicted = predicted_by_division[div_id]
            actual = [t["team_id"] for t in standings["divisions"][div_id]]
            per_division[div_id] = score_division(predicted, actual)

        total = sum(d["division_total"] for d in per_division.values())
        perfect_count = sum(1 for d in per_division.values() if d["perfect"])
        top2_count = sum(1 for d in per_division.values() if d["top2_bonus"])
        bottom2_count = sum(1 for d in per_division.values() if d["bottom2_bonus"])
        exact_hits = sum(d["exact_count"] for d in per_division.values())

        bettor_results[bid] = {
            "name": bettor["name"],
            "per_division": per_division,
            "total": total,
            "perfect_divisions_count": perfect_count,
            "top2_bonus_count": top2_count,
            "bottom2_bonus_count": bottom2_count,
            "total_exact_hits": exact_hits,
        }

    leaderboard = sorted(bettor_results.keys(), key=lambda bid: rank_key(bettor_results[bid]))

    # Flag unresolved ties after all four automatic tiebreakers.
    unresolved_ties = []
    for i in range(len(leaderboard) - 1):
        a, b = bettor_results[leaderboard[i]], bettor_results[leaderboard[i + 1]]
        if rank_key(a) == rank_key(b):
            unresolved_ties.append([leaderboard[i], leaderboard[i + 1]])

    output = {
        "season": season,
        "week": standings["week"],
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "standings_source": {
            "path": str(standings_path.relative_to(ROOT)),
            "fetched_at": standings["fetched_at"],
        },
        "bettors": bettor_results,
        "leaderboard": leaderboard,
        "unresolved_ties": unresolved_ties,
    }

    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SCORES_DIR / f"{season}-wk{standings['week']:02d}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"OK -- wrote {out_path}")
    print("\nLeaderboard:")
    for rank, bid in enumerate(leaderboard, start=1):
        r = bettor_results[bid]
        print(f"  {rank}. {r['name']:<12} {r['total']:>3} pts  "
              f"(perfect={r['perfect_divisions_count']} top2={r['top2_bonus_count']} "
              f"bot2={r['bottom2_bonus_count']} exact={r['total_exact_hits']}/32)")

    if unresolved_ties:
        print("\nUnresolved ties after tiebreakers #1-4 (would need #5, the point-total guess, which is unset):")
        for pair in unresolved_ties:
            print(f"  - {pair}")


if __name__ == "__main__":
    main()
