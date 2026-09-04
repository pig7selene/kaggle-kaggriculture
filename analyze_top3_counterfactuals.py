"""Economic decomposition for the exact Top-3 microtuning branch failures."""

from __future__ import annotations

from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import json
from pathlib import Path
from runpy import run_path
import statistics

from kaggle_environments import make

from analyze_top3_forensics import economic_timelines
from run_epic_experiments import _independent_shop_schedule, _run_with_fixed_shops
from run_post_opening_validation import _load_opponent
from run_v27_replay_backbone import _inventory_value, _semantic_validate, _transition_metrics


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "experiments/top3_counterfactual_decomposition.json"
BASELINE = "agents/top50_distilled/top50_observable_portfolio.py"
SCENARIOS = {
    "rank3_signature": {
        "candidate": "agents/top3_tuned/top3_tuned_a_rank3_swap.py",
        "opponent": "agents/top3_tuned/raw_rank3_oceanmix.py",
    },
    "currentbest_alias": {
        "candidate": "agents/top3_tuned/top3_tuned_a_rank3_swap.py",
        "opponent": BASELINE,
    },
    "k3_signature": {
        "candidate": "agents/top3_tuned/top3_tuned_b_k3_swap.py",
        "opponent": "agents/v27_replay_weed_guard.py",
    },
    "rank1_medoid_vs_baseline": {
        "candidate": "agents/top3_tuned/raw_rank1_tetsuya.py",
        "opponent": "agents/v27_replay_weed_guard.py",
    },
    "rank2_medoid_vs_baseline": {
        "candidate": "agents/top3_tuned/raw_rank2_crop_dusta.py",
        "opponent": "agents/v27_replay_weed_guard.py",
    },
    "rank3_medoid_vs_baseline": {
        "candidate": "agents/top3_tuned/raw_rank3_oceanmix.py",
        "opponent": "agents/v27_replay_weed_guard.py",
    },
}


def totals(timeline):
    revenue, sales, harvests = Counter(), Counter(), Counter()
    seeds, feed, animals = Counter(), Counter(), Counter()
    for row in timeline:
        revenue.update(row["sale_revenue"]); sales.update(row["sales"]); harvests.update(row["harvests"])
        seeds.update(row["seed_spending"]); feed.update(row["feed_spending"]); animals.update(row["animal_spending"])
    return {
        "sale_revenue": dict(revenue), "sale_quantity": dict(sales), "harvest_quantity": dict(harvests),
        "crop_revenue": sum(revenue[item] for item in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")),
        "livestock_revenue": sum(revenue[item] for item in ("EGG", "MILK", "WOOL")),
        "fertilizer_revenue": revenue["FERTILIZER"],
        "seed_spending": dict(seeds), "feed_spending": dict(feed), "animal_spending": dict(animals),
        "land_spending": sum(row["land_spending"] for row in timeline),
        "labor_spending": sum(row["labor_spending"] for row in timeline),
        "total_revenue": sum(revenue.values()),
        "total_spending": sum(row["total_spending"] for row in timeline),
    }


def animal_counts(farm):
    counts = Counter()
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal"):
                counts[tile["animal"]] += 1
    return counts


def run_job(job):
    key, scenario, role, agent_path, opponent_path, seed, seat, mode = job
    candidate = run_path(str(ROOT / agent_path))["agent"]
    opponent = _load_opponent(opponent_path)
    semantic = []
    def checked(obs):
        action = candidate(obs)
        try:
            _semantic_validate(obs, action)
        except Exception as error:
            semantic.append({"step": int(obs["step"]), "error": repr(error)})
        return action
    pair = [opponent, opponent]
    pair[seat] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    if mode == "fixed":
        _run_with_fixed_shops(env, pair, _independent_shop_schedule(seed))
    else:
        env.run(pair)
    replay = env.toJSON()
    timelines, mismatches = economic_timelines(replay)
    transition = _transition_metrics(replay, seat)
    final = env.steps[-1]
    stranded_value, stranded = _inventory_value(final[seat])
    previous = Counter()
    escapes = Counter()
    for states in replay["steps"]:
        obs = states[seat]["observation"]
        owned = animal_counts(obs["farms"][seat])
        private = obs["private"]
        for animal in ("GOOSE", "COW", "SHEEP"):
            owned[animal] += int(private.get("shed", {}).get(animal, 0))
            owned[animal] += sum(int(inv.get(animal, 0)) for inv in private.get("inventories", []))
            if owned[animal] < previous[animal]:
                escapes[animal] += previous[animal] - owned[animal]
        previous = owned
    daily = []
    for day, row in enumerate(timelines[seat]):
        daily.append({
            "day": day, "bank_end": row["bank_end"], "productive": row["farm"].get("productive", 0),
            "hands": row["farm"].get("hands", 0), "quadrants": row["farm"].get("quadrants", 0),
            "crops": row["farm"].get("crops", {}), "animals": row["farm"].get("animals", {}),
            "revenue": row["total_sale_revenue"], "spending": row["total_spending"],
        })
    telemetry = dict(candidate.telemetry)
    return {
        "key": key, "scenario": scenario, "role": role, "agent": agent_path,
        "opponent": opponent_path, "seed": seed, "seat": seat, "mode": mode,
        "money": float(final[seat].reward), "opponent_money": float(final[1 - seat].reward),
        "advantage": float(final[seat].reward - final[1 - seat].reward),
        "economy": totals(timelines[seat]), "opponent_economy": totals(timelines[1 - seat]),
        "daily": daily, "transition": transition, "semantic_failures": semantic,
        "actual_livestock_escapes": dict(escapes), "stranded_value": stranded_value,
        "stranded": stranded, "portfolio_parent": telemetry.get("portfolio_parent"),
        "reconciliation_events": len(mismatches),
    }


def jobs():
    output = []
    for scenario, config in SCENARIOS.items():
        for mode, seed in (("fixed", 1261100), ("natural", 1261200)):
            for seat in (0, 1):
                for role, path in (("baseline", BASELINE), ("candidate", config["candidate"])):
                    key = f"{scenario}|{mode}|{seed}|{seat}|{role}"
                    output.append((key, scenario, role, path, config["opponent"], seed, seat, mode))
    return output


def durable_day(candidate, baseline):
    deltas = [left["bank_end"] - right["bank_end"] for left, right in zip(candidate["daily"], baseline["daily"])]
    final_sign = 1 if deltas[-1] > 0 else -1 if deltas[-1] < 0 else 0
    day = None
    if final_sign:
        for index in range(len(deltas)):
            if deltas[index] * final_sign > 0 and all(value * final_sign > 0 for value in deltas[index:]):
                day = index
                break
    return day, deltas


def main():
    games = []
    with ProcessPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(run_job, job) for job in jobs()]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            print(f"decomposition {index}/{len(futures)}", flush=True)
    paired = []
    by_condition = defaultdict(dict)
    for row in games:
        condition = "|".join(row["key"].split("|")[:-1])
        by_condition[condition][row["role"]] = row
    for condition, rows in sorted(by_condition.items()):
        candidate, baseline = rows["candidate"], rows["baseline"]
        first_durable, bank_deltas = durable_day(candidate, baseline)
        economic_delta = {}
        for field in ("crop_revenue", "livestock_revenue", "fertilizer_revenue", "land_spending", "labor_spending", "total_revenue", "total_spending"):
            economic_delta[field] = candidate["economy"][field] - baseline["economy"][field]
        paired.append({
            "condition": condition, "scenario": candidate["scenario"], "mode": candidate["mode"],
            "seed": candidate["seed"], "seat": candidate["seat"],
            "candidate_parent": candidate["portfolio_parent"], "baseline_parent": baseline["portfolio_parent"],
            "own_money_delta": candidate["money"] - baseline["money"],
            "advantage_delta": candidate["advantage"] - baseline["advantage"],
            "first_durable_bank_divergence_day": first_durable, "daily_bank_delta": bank_deltas,
            "economic_delta": economic_delta,
            "crop_death_delta": candidate["transition"]["crop_deaths"] - baseline["transition"]["crop_deaths"],
            "candidate_actual_escapes": candidate["actual_livestock_escapes"],
            "baseline_actual_escapes": baseline["actual_livestock_escapes"],
        })
    scenario_summary = {}
    for scenario in SCENARIOS:
        rows = [row for row in paired if row["scenario"] == scenario]
        scenario_summary[scenario] = {
            "pairs": len(rows), "own_money_delta_mean": statistics.fmean(row["own_money_delta"] for row in rows),
            "advantage_delta_mean": statistics.fmean(row["advantage_delta"] for row in rows),
            "first_durable_divergence_day_median": statistics.median(row["first_durable_bank_divergence_day"] for row in rows if row["first_durable_bank_divergence_day"] is not None),
            "economic_delta_mean": {
                field: statistics.fmean(row["economic_delta"][field] for row in rows)
                for field in rows[0]["economic_delta"]
            },
            "crop_death_delta_mean": statistics.fmean(row["crop_death_delta"] for row in rows),
            "candidate_escapes": sum(sum(row["candidate_actual_escapes"].values()) for row in rows),
        }
    OUTPUT.write_text(json.dumps({
        "schema_version": 1,
        "design": "Same initial state, identical opponent/seed/seat/shop path; only one coherent parent continuation differs. Shared-market response is part of the treatment effect.",
        "games": games, "paired": paired, "scenario_summary": scenario_summary,
    }, indent=2, sort_keys=True) + "\n")
    print(OUTPUT)
    print(json.dumps(scenario_summary, indent=2))


if __name__ == "__main__":
    main()
