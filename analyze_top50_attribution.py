"""Paired economic attribution for the locked Top-50 finalist versus V2."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
from runpy import run_path
import statistics

from kaggle_environments import make

from mine_top50_strategies import _economic_timeline
from run_epic_experiments import _independent_shop_schedule, _run_with_fixed_shops
from run_post_opening_validation import _load_opponent


ROOT = Path(__file__).resolve().parent
BASELINE = "agents/super_replay_v2/super_backbone_v2.py"
FINALIST = "agents/top50_distilled/top50_observable_portfolio.py"
OUTPUT = ROOT / "experiments/top50_economic_attribution.json"


def _sum_map(timeline, field):
    total = Counter()
    for row in timeline: total.update(row[field])
    return dict(total)


def _run(candidate_path, seed, seat, natural):
    candidate = run_path(str(ROOT / candidate_path))["agent"]
    rival = _load_opponent(BASELINE)
    pair = [rival, rival]; pair[seat] = candidate
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    if natural: env.run(pair)
    else: _run_with_fixed_shops(env, pair, _independent_shop_schedule(seed))
    replay = env.toJSON()
    timeline, reconciliation = _economic_timeline(replay, seat)
    final = replay["steps"][-1]
    sales = _sum_map(timeline, "sale_quantity")
    revenue = _sum_map(timeline, "sale_revenue")
    costs = {
        "seeds": sum(sum(row["seed_spend"].values()) for row in timeline),
        "animals": sum(sum(row["animal_spend"].values()) for row in timeline),
        "feed_and_products": sum(sum(row["product_spend"].values()) for row in timeline),
        "hands": sum(row["labor_spend"] for row in timeline),
        "land": sum(row["land_spend"] for row in timeline),
    }
    return {
        "candidate": candidate_path, "seed": seed, "seat": seat, "mode": "natural" if natural else "fixed",
        "money": float(final[seat]["reward"]), "opponent_money": float(final[1-seat]["reward"]),
        "revenue": revenue, "sales": sales, "costs": costs,
        "planted": _sum_map(timeline, "plant_quantity"), "harvested": _sum_map(timeline, "harvest_quantity"),
        "realized_average_prices": {item: revenue[item] / quantity for item, quantity in sales.items() if quantity},
        "reconciliation_events": len(reconciliation),
    }


def _mean_maps(rows, field):
    keys = sorted({key for row in rows for key in row[field]})
    return {key: statistics.fmean(row[field].get(key, 0) for row in rows) for key in keys}


def main():
    games = []
    for seed in range(1109400, 1109404):
        for natural in (False, True):
            for seat in (0, 1):
                for candidate in (BASELINE, FINALIST):
                    games.append(_run(candidate, seed, seat, natural))
                    print(candidate.split("/")[-1], seed, natural, seat, flush=True)
    summaries = {}
    for candidate in (BASELINE, FINALIST):
        rows = [row for row in games if row["candidate"] == candidate]
        summaries[candidate] = {
            "games": len(rows), "average_money": statistics.fmean(row["money"] for row in rows),
            "average_opponent_money": statistics.fmean(row["opponent_money"] for row in rows),
            "revenue": _mean_maps(rows, "revenue"), "sales": _mean_maps(rows, "sales"),
            "costs": _mean_maps(rows, "costs"), "planted": _mean_maps(rows, "planted"),
            "harvested": _mean_maps(rows, "harvested"),
            "realized_average_prices": _mean_maps(rows, "realized_average_prices"),
        }
    base, candidate = summaries[BASELINE], summaries[FINALIST]
    def delta(field):
        keys = sorted(set(base[field]) | set(candidate[field]))
        return {key: candidate[field].get(key, 0) - base[field].get(key, 0) for key in keys}
    payload = {
        "schema_version": 1, "design": "four untouched seeds, fixed and natural shops, both seats, finalist and V2 each against V2",
        "games": games, "summary": summaries,
        "delta_finalist_minus_v2": {
            "own_money": candidate["average_money"] - base["average_money"],
            "opponent_money": candidate["average_opponent_money"] - base["average_opponent_money"],
            "net_advantage": (candidate["average_money"] - candidate["average_opponent_money"]) - (base["average_money"] - base["average_opponent_money"]),
            "revenue": delta("revenue"), "sales": delta("sales"), "costs": delta("costs"),
            "planted": delta("planted"), "harvested": delta("harvested"),
            "realized_average_prices": delta("realized_average_prices"),
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
