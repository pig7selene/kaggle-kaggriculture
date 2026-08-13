"""Controlled staged-land search on top of the frozen four-cow C2 economy."""

from __future__ import annotations

import argparse
import copy
import json
import math
import statistics
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from benchmark import DEFAULT_WORKERS, EXPERIMENTS_DIR, ROOT, _file_sha256, _load_agent


ENGINE_PATH = ROOT / "agents" / "animal_land_common.py"
ENGINE = run_path(str(ENGINE_PATH))
BASE = copy.deepcopy(ENGINE["C2_LAND_BASE"])
CROP_SEED_COST = {crop: data["seed"] for crop, data in ENGINE["CROPS"].items()}
LAND_COSTS = tuple(ENGINE["LAND_COSTS"])
SELLABLE = set(ENGINE["BASE_PRICES"])

OPPONENTS = {
    "melon_scale_12": ROOT / "agents" / "melon_scale_12.py",
    "proxy_melon_heavy": ROOT / "agents" / "proxies" / "melon_heavy.py",
    "proxy_phased_rotation": ROOT / "agents" / "proxies" / "phased_rotation.py",
    "proxy_land_expander": ROOT / "agents" / "proxies" / "land_expander.py",
    "proxy_inventory_holder": ROOT / "agents" / "proxies" / "inventory_holder.py",
    "proxy_mixed_crop": ROOT / "agents" / "proxies" / "mixed_crop.py",
    "proxy_livestock_crop": ROOT / "agents" / "proxies" / "livestock_crop.py",
    "proxy_high_labor": ROOT / "agents" / "proxies" / "high_labor.py",
    "adaptive_c_phased": ROOT / "agents" / "adaptive_c_phased.py",
    "animal_c2_cows": ROOT / "agents" / "animal_c2_cows.py",
}
CORE_OPPONENTS = {
    name: OPPONENTS[name]
    for name in (
        "proxy_livestock_crop",
        "proxy_high_labor",
        "proxy_land_expander",
        "proxy_phased_rotation",
        "adaptive_c_phased",
        "animal_c2_cows",
    )
}


def _fib(index):
    a, b = 1, 1
    for _ in range(index):
        a, b = b, a + b
    return a


def _productive_tiles(farm):
    return sum(
        1
        for row in farm["tiles"]
        for tile in row
        if isinstance(tile, dict)
        and (tile.get("kind") == "PLANT" or tile.get("animal") is not None)
    )


def _cow_count(farm):
    return sum(
        1
        for row in farm["tiles"]
        for tile in row
        if isinstance(tile, dict) and tile.get("animal") == "COW"
    )


def _stranded_units(final_state, seat):
    private = final_state.observation["private"]
    total = sum(private["shed"].get(item, 0) for item in SELLABLE)
    total += sum(
        inventory.get(item, 0)
        for inventory in private["inventories"]
        for item in SELLABLE
    )
    farm = final_state.observation["farms"][seat]
    total += sum(
        tile.get("yield_units", 0)
        for row in farm["tiles"]
        for tile in row
        if isinstance(tile, dict) and tile.get("animal")
    )
    return total


def _run_game(job):
    variant, config, opponent_name, opponent_path, seed, seat = job
    namespace = run_path(str(ENGINE_PATH))
    candidate = namespace["make_agent"](config)
    runtime_config = candidate.config
    opponent = _load_agent(opponent_path)
    productive = []
    operation_counts = Counter()
    land_events = []
    labor_cost = 0
    seed_spending = 0
    cow_spending = 0
    wheat_spending = 0
    land_spending = 0
    peak_cows = 0
    escaped_cows = 0
    reached_four = False

    def tracked(obs):
        nonlocal labor_cost, seed_spending, cow_spending, wheat_spending
        nonlocal land_spending, peak_cows, escaped_cows, reached_four
        action = candidate(obs)
        me = obs["farms"][obs["player"]]
        current_cows = _cow_count(me)
        peak_cows = max(peak_cows, current_cows)
        if current_cows == 4:
            reached_four = True
        if reached_four and current_cows < 4:
            escaped_cows = max(escaped_cows, 4 - current_cows)
        if obs["hour"] == 23:
            productive.append(_productive_tiles(me))
        for unit_action in [action["farmer"], *action["hands"]]:
            operation_counts[unit_action[0]] += 1
        next_hire = me.get("hires_today", 0)
        purchases_before = len(me["unlocked_quadrants"]) - 1
        for order in action["market"]:
            operation_counts[order[0]] += 1
            if order[0] == "HIRE":
                labor_cost += _fib(next_hire)
                next_hire += 1
            elif order[0] == "BUY_SEED":
                seed_spending += CROP_SEED_COST[order[1]] * order[2]
            elif order[0] == "BUY_ANIMAL":
                cow_spending += namespace["ANIMALS"][order[1]]["cost"] * order[2]
            elif order[0] == "BUY_PRODUCT" and order[1] == "WHEAT":
                wheat_spending += obs["market"]["prices"]["WHEAT"] * order[2]
            elif order[0] == "BUY_LAND":
                economics = namespace["_land_economics"](obs, runtime_config)
                if economics is None:
                    raise RuntimeError("BUY_LAND emitted without an economic estimate")
                land_spending += LAND_COSTS[purchases_before]
                land_events.append(economics)
                purchases_before += 1
        return action

    agents = [opponent, opponent]
    agents[seat] = tracked
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": seed},
        debug=True,
    )
    env.run(agents)
    final = env.steps[-1]
    statuses = [state.status for state in final]
    if len(env.steps) != 720 or statuses != ["DONE", "DONE"]:
        raise RuntimeError(
            f"failed {variant} vs {opponent_name} seed={seed} seat={seat}: "
            f"turns={len(env.steps)} statuses={statuses}"
        )
    final_cows = _cow_count(final[seat].observation["farms"][seat])
    if reached_four and final_cows < 4:
        escaped_cows = max(escaped_cows, 4 - final_cows)
    candidate_money = float(final[seat].reward)
    opponent_money = float(final[1 - seat].reward)
    return {
        "variant": variant,
        "opponent": opponent_name,
        "seed": seed,
        "seat": seat,
        "candidate_money": candidate_money,
        "opponent_money": opponent_money,
        "advantage": candidate_money - opponent_money,
        "productive_tiles": statistics.fmean(productive) if productive else 0.0,
        "labor_cost": labor_cost,
        "seed_spending": seed_spending,
        "cow_spending": cow_spending,
        "wheat_spending": wheat_spending,
        "land_spending": land_spending,
        "land_events": land_events,
        "workload": dict(operation_counts),
        "peak_cows": peak_cows,
        "final_cows": final_cows,
        "escaped_cows": escaped_cows,
        "stranded_units": _stranded_units(final[seat], seat),
    }


def _percentile(values, fraction):
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = fraction * (len(ordered) - 1)
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _summary(games):
    advantages = [game["advantage"] for game in games]
    money = [game["candidate_money"] for game in games]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    ties = len(games) - wins - losses
    seed_groups = {}
    for game in games:
        seed_groups.setdefault(game["seed"], []).append(game["advantage"])
    seed_advantages = [statistics.fmean(values) for values in seed_groups.values()]
    events_by_quadrant = {}
    for game in games:
        for event in game["land_events"]:
            events_by_quadrant.setdefault(event["quadrant_number"], []).append(event)
    land = {
        str(quadrant): {
            "purchases": len(events),
            "average_purchase_day": statistics.fmean(e["purchase_day"] for e in events),
            "average_land_cost": statistics.fmean(e["land_cost"] for e in events),
            "average_seed_cost": statistics.fmean(e["seed_cost"] for e in events),
            "average_additional_labor_cost": statistics.fmean(
                e["additional_labor_cost"] for e in events
            ),
            "average_expected_harvests": statistics.fmean(
                e["expected_harvests"] for e in events
            ),
            "average_expected_payback_day": statistics.fmean(
                e["payback_day"] for e in events if e["payback_day"] is not None
            ),
            "average_expected_roi": statistics.fmean(e["roi"] for e in events),
        }
        for quadrant, events in sorted(events_by_quadrant.items())
    }
    workload_ops = ("WATER", "HARVEST", "FEED", "CARE", "COLLECT_FERTILIZER",
                    "NORTH", "SOUTH", "EAST", "WEST", "PASS")
    workload = {
        op: statistics.fmean(game["workload"].get(op, 0) for game in games)
        for op in workload_ops
    }
    return {
        "games": len(games),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": wins / len(games),
        "score_rate": (wins + 0.5 * ties) / len(games),
        "average_money": statistics.fmean(money),
        "average_advantage": statistics.fmean(advantages),
        "p10_advantage": _percentile(seed_advantages, 0.10),
        "money_variance": statistics.pvariance(money),
        "advantage_variance": statistics.pvariance(advantages),
        "average_productive_tiles": statistics.fmean(g["productive_tiles"] for g in games),
        "average_labor_cost": statistics.fmean(g["labor_cost"] for g in games),
        "average_seed_spending": statistics.fmean(g["seed_spending"] for g in games),
        "average_wheat_spending": statistics.fmean(g["wheat_spending"] for g in games),
        "average_land_spending": statistics.fmean(g["land_spending"] for g in games),
        "average_land_purchases": statistics.fmean(len(g["land_events"]) for g in games),
        "land": land,
        "workload": workload,
        "max_escaped_cows": max(g["escaped_cows"] for g in games),
        "max_stranded_units": max(g["stranded_units"] for g in games),
    }


def _variant_result(name, config, games, opponents):
    overall = _summary(games)
    matchups = {
        opponent: _summary([game for game in games if game["opponent"] == opponent])
        for opponent in opponents
    }
    worst = min(
        matchups,
        key=lambda opponent: (
            matchups[opponent]["score_rate"],
            matchups[opponent]["average_advantage"],
        ),
    )
    matchup_wins = sum(row["wins"] > row["losses"] for row in matchups.values())
    matchup_losses = sum(row["wins"] < row["losses"] for row in matchups.values())
    key_names = [
        name for name in ("animal_c2_cows", "proxy_livestock_crop",
                          "proxy_high_labor", "proxy_land_expander")
        if name in matchups
    ]
    key_advantage = statistics.fmean(matchups[name]["average_advantage"] for name in key_names)
    search_score = (
        overall["average_advantage"]
        + 0.25 * overall["p10_advantage"]
        + 0.30 * key_advantage
        + 0.15 * matchups[worst]["average_advantage"]
        + 1000 * (matchup_wins - matchup_losses)
    )
    return {
        "variant": name,
        "config": config,
        "overall": overall,
        "matchups": matchups,
        "matchup_wins": matchup_wins,
        "matchup_losses": matchup_losses,
        "matchup_ties": len(matchups) - matchup_wins - matchup_losses,
        "worst_opponent": worst,
        "search_score": search_score,
    }


def _evaluate(stage, variants, opponents, seeds, workers):
    jobs = [
        (name, config, opponent, str(path), seed, seat)
        for name, config in variants.items()
        for opponent, path in opponents.items()
        for seed in seeds
        for seat in (0, 1)
    ]
    games = []
    if workers == 1:
        for index, job in enumerate(jobs, 1):
            games.append(_run_game(job))
            if index % 50 == 0 or index == len(jobs):
                print(f"{stage}: {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_run_game, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), 1):
                games.append(future.result())
                if index % 50 == 0 or index == len(jobs):
                    print(f"{stage}: {index}/{len(jobs)}", flush=True)
    rows = [
        _variant_result(
            name,
            variants[name],
            [game for game in games if game["variant"] == name],
            opponents,
        )
        for name in variants
    ]
    rows.sort(key=lambda row: row["search_score"], reverse=True)
    return {
        "stage": stage,
        "seeds": list(seeds),
        "opponents": list(opponents),
        "games_per_variant": len(opponents) * len(seeds) * 2,
        "results": rows,
        "games": games,
    }


def _screen_variants():
    variants = {"A_no_land": copy.deepcopy(BASE)}
    for letter, day in (("B", 11), ("C", 14), ("D", 16), ("E", 18)):
        config = copy.deepcopy(BASE)
        config.update({"max_land_purchases": 1, "land_purchase_days": (day,)})
        variants[f"{letter}_fixed_day{day}"] = config
    payback = copy.deepcopy(BASE)
    payback.update({"land_policy": "cow_payback", "max_land_purchases": 1,
                    "land_cow_payback_day": 20})
    variants["F_cow_payback"] = payback
    dynamic = copy.deepcopy(BASE)
    dynamic.update({"land_policy": "dynamic_roi", "max_land_purchases": 1,
                    "land_min_day": 11, "land_bank_thresholds": (9000,),
                    "land_roi_hurdle": 0.10})
    variants["G_dynamic_roi"] = dynamic
    return variants


def _allocation_variants(timing_row):
    variants = {}
    for allocation in ("wheat_heavy", "strawberry_heavy",
                       "phased_wheat_strawberry", "adaptive", "feed_support"):
        for capacity in (4, 8, 12):
            config = copy.deepcopy(timing_row["config"])
            config.update({
                "new_land_allocation": allocation,
                "land_labor_mode": "staged",
                "land_plots_per_added_hand": capacity,
            })
            variants[f"{timing_row['variant']}__{allocation}__labor{capacity}"] = config
    return variants


def _scale_variants(rows):
    variants = {}
    for row in rows:
        for quadrants in (1, 2, 3):
            for hurdle in (0.0, 0.15):
                config = copy.deepcopy(row["config"])
                config["max_land_purchases"] = quadrants
                config["land_roi_hurdle"] = hurdle
                policy = config.get("land_policy")
                if policy == "fixed":
                    first = config["land_purchase_days"][0]
                    config["land_purchase_days"] = tuple(
                        (first, min(20, first + 4), min(23, first + 7))[:quadrants]
                    )
                elif policy == "dynamic_roi":
                    first_threshold = config.get("land_bank_thresholds", (9000,))[0]
                    config["land_bank_thresholds"] = tuple(
                        (first_threshold, first_threshold + 5000, first_threshold + 11000)[:quadrants]
                    )
                name = f"{row['variant']}__q{quadrants}__roi{hurdle:.2f}"
                variants[name] = config
    return variants


def _write_markdown(path, result):
    lines = [
        "# C2 Cow Staged-Land Search",
        "",
        "All stages use deterministic seeds and both player positions. Search and held-out seeds are disjoint.",
        "",
    ]
    for stage in result["stages"]:
        lines.extend([
            f"## {stage['stage']}", "",
            f"Seeds: {stage['seeds']}; games per variant: {stage['games_per_variant']}.", "",
            "| Rank | Variant | W/L/T | Win rate | Avg money | Avg advantage | P10 | Variance | Tiles | Labor | Land | Worst |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ])
        for rank, row in enumerate(stage["results"], 1):
            overall = row["overall"]
            worst = row["matchups"][row["worst_opponent"]]
            lines.append(
                f"| {rank} | {row['variant']} | {overall['wins']}/{overall['losses']}/{overall['ties']} | "
                f"{overall['win_rate']*100:.1f}% | {overall['average_money']:.1f} | "
                f"{overall['average_advantage']:+.1f} | {overall['p10_advantage']:+.1f} | "
                f"{overall['money_variance']:.1f} | {overall['average_productive_tiles']:.2f} | "
                f"{overall['average_labor_cost']:.1f} | {overall['average_land_purchases']:.2f} | "
                f"{row['worst_opponent']} ({worst['wins']}/{worst['losses']}/{worst['ties']}, "
                f"{worst['average_advantage']:+.1f}) |"
            )
        lines.append("")
    final = result["stages"][-1]["results"]
    lines.extend(["## Held-out matchup details", ""])
    for row in final:
        lines.extend([
            f"### {row['variant']}", "",
            "| Opponent | W/L/T | Avg money | Avg advantage | P10 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ])
        for opponent, summary in row["matchups"].items():
            lines.append(
                f"| {opponent} | {summary['wins']}/{summary['losses']}/{summary['ties']} | "
                f"{summary['average_money']:.1f} | {summary['average_advantage']:+.1f} | "
                f"{summary['p10_advantage']:+.1f} |"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(workers):
    screen = _evaluate(
        "timing_screen", _screen_variants(), OPPONENTS, range(9400, 9402), workers
    )
    best_timing = next(row for row in screen["results"] if row["variant"] != "A_no_land")
    allocation = _evaluate(
        "allocation_labor_search",
        _allocation_variants(best_timing),
        CORE_OPPONENTS,
        range(9420, 9422),
        workers,
    )
    scale = _evaluate(
        "quadrant_roi_search",
        _scale_variants(allocation["results"][:2]),
        CORE_OPPONENTS,
        range(9440, 9442),
        workers,
    )
    best_expansion = scale["results"][0]
    confirmation_variants = {
        "C2_no_land": copy.deepcopy(BASE),
        "best_expansion": copy.deepcopy(best_expansion["config"]),
    }
    heldout = _evaluate(
        "heldout_confirmation",
        confirmation_variants,
        OPPONENTS,
        range(9600, 9613),
        workers,
    )
    result = {
        "schema_version": 1,
        "experiment": "c2_cow_staged_land",
        "engine": str(ENGINE_PATH.relative_to(ROOT)),
        "engine_sha256": _file_sha256(ENGINE_PATH),
        "opponents": {name: str(path.relative_to(ROOT)) for name, path in OPPONENTS.items()},
        "opponent_sha256": {name: _file_sha256(path) for name, path in OPPONENTS.items()},
        "search_seed_ranges": {
            "timing": [9400, 9401], "allocation_labor": [9420, 9421],
            "quadrants_roi": [9440, 9441], "heldout": [9600, 9612],
        },
        "selected_search_variant": best_expansion,
        "stages": [screen, allocation, scale, heldout],
    }
    json_path = EXPERIMENTS_DIR / "cow_land_search.json"
    md_path = EXPERIMENTS_DIR / "cow_land_search.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    _write_markdown(md_path, result)
    print(f"Saved {json_path}")
    print(f"Saved {md_path}")
    for row in heldout["results"]:
        overall = row["overall"]
        print(
            f"HELDOUT {row['variant']}: {overall['wins']}/{overall['losses']}/{overall['ties']} "
            f"money={overall['average_money']:.2f} adv={overall['average_advantage']:+.2f} "
            f"p10={overall['p10_advantage']:+.2f} land={overall['average_land_purchases']:.2f}"
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = parser.parse_args()
    run(args.workers)


if __name__ == "__main__":
    main()
