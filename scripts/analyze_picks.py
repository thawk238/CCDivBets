"""Compute fun-facts stats from the locked preseason picks (data/picks.json).

Picks never change once entered, so this only needs to be re-run if the
picks file changes (e.g. a correction). Output feeds the preseason
write-up content, not the weekly scoring pipeline.

Writes data/preseason_facts.json:
  - per-division slot tallies, distinct-ordering counts, unanimous slots
  - league-wide: most/least varied division, any fully unanimous division,
    any team that got locked into a slot by every bettor
  - per-bettor: "lone wolf" picks (a team/slot combo nobody else picked)
    and their 8 first-place picks (who they need to actually finish 1st)
"""

import json
from collections import Counter
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    divisions_data = load_json(DATA_DIR / "divisions.json")
    bettors_data = load_json(DATA_DIR / "bettors.json")
    picks_data = load_json(DATA_DIR / "picks.json")

    team_name = {}
    for div in divisions_data["divisions"]:
        for t in div["teams"]:
            team_name[t["id"]] = t["name"]

    bettors = bettors_data["bettors"]
    num_bettors = len(bettors)
    picks = picks_data["picks"]

    division_stats = {}
    for div in divisions_data["divisions"]:
        div_id = div["id"]
        orderings = [tuple(picks[b["id"]][div_id]) for b in bettors]
        distinct_orderings = len(set(orderings))

        slot_tallies = {}
        for slot in range(4):
            tally = Counter(order[slot] for order in orderings)
            slot_tallies[str(slot + 1)] = dict(tally)

        near_unanimous = []
        for slot_str, tally in slot_tallies.items():
            team, count = max(tally.items(), key=lambda kv: kv[1])
            if count >= max(4, num_bettors - 1):  # unanimous or a single holdout
                near_unanimous.append(
                    {
                        "slot": int(slot_str),
                        "team": team,
                        "team_name": team_name[team],
                        "count": count,
                        "total": num_bettors,
                        "unanimous": count == num_bettors,
                    }
                )

        division_stats[div_id] = {
            "name": div["name"],
            "distinct_orderings": distinct_orderings,
            "unanimous": distinct_orderings == 1,
            "slot_tallies": slot_tallies,
            "near_unanimous_slots": near_unanimous,
        }

    most_variation = max(division_stats.items(), key=lambda kv: kv[1]["distinct_orderings"])
    least_variation = min(division_stats.items(), key=lambda kv: kv[1]["distinct_orderings"])
    unanimous_divisions = [d for d, s in division_stats.items() if s["unanimous"]]

    locked_slots = []
    for div_id, s in division_stats.items():
        for slot in s["near_unanimous_slots"]:
            if slot["unanimous"]:
                locked_slots.append({**slot, "division": div_id, "division_name": s["name"]})

    identical_submissions = []
    for a, b in combinations(bettors, 2):
        a_picks = picks[a["id"]]
        b_picks = picks[b["id"]]
        if all(a_picks[d] == b_picks[d] for d in a_picks):
            identical_submissions.append([a["name"], b["name"]])

    bettor_stats = {}
    for bettor in bettors:
        bid = bettor["id"]
        lone_wolf = []
        top_picks = []
        for div in divisions_data["divisions"]:
            div_id = div["id"]
            my_order = picks[bid][div_id]
            top_picks.append({"division": div_id, "division_name": div["name"], "team": my_order[0], "team_name": team_name[my_order[0]]})
            for slot in range(4):
                team = my_order[slot]
                tally = division_stats[div_id]["slot_tallies"][str(slot + 1)]
                if tally.get(team, 0) == 1:
                    lone_wolf.append(
                        {
                            "division": div_id,
                            "division_name": div["name"],
                            "slot": slot + 1,
                            "team": team,
                            "team_name": team_name[team],
                        }
                    )
        bettor_stats[bid] = {
            "name": bettor["name"],
            "lone_wolf_picks": lone_wolf,
            "top_picks": top_picks,
        }

    output = {
        "num_bettors": num_bettors,
        "divisions": division_stats,
        "league_wide": {
            "most_variation_division": most_variation[0],
            "most_variation_count": most_variation[1]["distinct_orderings"],
            "least_variation_division": least_variation[0],
            "least_variation_count": least_variation[1]["distinct_orderings"],
            "unanimous_divisions": unanimous_divisions,
            "locked_slots": locked_slots,
            "identical_submissions": identical_submissions,
        },
        "bettors": bettor_stats,
    }

    out_path = DATA_DIR / "preseason_facts.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"OK -- wrote {out_path}")


if __name__ == "__main__":
    main()
