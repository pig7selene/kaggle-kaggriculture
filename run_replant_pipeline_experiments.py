"""Controlled harvest-to-replant pipeline ablations and diagnostics."""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from runpy import run_path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_crop_lifecycle import lifecycle_metrics
from analyze_post_opening_real_gap import _field_analysis
from analyze_replant_pipeline import _event_rows, _summary as _replant_summary
from analyze_top_player_replays import _transition_ledger
from run_post_opening_validation import (
    LOSS_EPISODES,
    REPLAY_DERIVED,
    REPLAY_DIR,
    ROOT,
    _load_opponent,
    _trace_spec,
)
from test_economic_agents import SELLABLE, _validate_action


CANDIDATES = {
    "P0": "agents/replant_p0_current.py",
    "P1_seed_semantic_control": "agents/replant_p1_seed_preload.py",
    "P2_predictive": "agents/replant_p2_predictive.py",
    "P3_safe_chain": "agents/replant_p3_safe_chain.py",
    "P3b_recent_empty": "agents/replant_p3b_recent_empty.py",
    "P3c_inventory_chain": "agents/replant_p3c_inventory_chain.py",
    "P3d_pending_chain": "agents/replant_p3d_pending_chain.py",
    "P3e_safe_exact_chain": "agents/replant_p3e_safe_exact_chain.py",
    "P3f_opening_chain": "agents/replant_p3f_opening_chain.py",
    "P3g_extended_chain": "agents/replant_p3g_extended_chain.py",
    "P3h_protected_exact": "agents/replant_p3h_protected_exact.py",
    "P3i_bounded_exact": "agents/replant_p3i_bounded_exact.py",
    "P4_cohort": "agents/replant_p4_cohort.py",
    "P5_combined": "agents/replant_p5_combined.py",
    "P6_cows6": "agents/replant_p6_cows6.py",
    "P7_cows7": "agents/replant_p7_cows7.py",
    "P8_cows8": "agents/replant_p8_cows8.py",
    "P9_cows9": "agents/replant_p9_cows9.py",
    "C6_no_pipeline": "agents/replant_cow6_control.py",
    "C7_no_pipeline": "agents/replant_cow7_control.py",
    "C8_no_pipeline": "agents/replant_cow8_control.py",
    "C6_guarded": "agents/replant_cow6_guarded.py",
}
REAL_NAMES = {
    92008833: "Jayveer", 92009080: "Lucas",
    92010768: "Pedro", 92011750: "Alexander",
}
HARD_POOL = {
    **REPLAY_DERIVED,
    "epic_jay_wave": "agents/adversaries/epic_jay_capital_wave.py",
    "epic_pedro_trader": "agents/adversaries/epic_pedro_demand_trader.py",
    "high_labor": "agents/proxies/high_labor.py",
    "land_expander": "agents/proxies/land_expander.py",
    "livestock_crop": "agents/proxies/livestock_crop.py",
    "gen_cow6_d8": "agents/adversaries/gen_cow6_d8.py",
}
CROPS = tuple(game.CROPS)
ANIMAL_PRODUCTS = ("EGG", "MILK", "WOOL", "FERTILIZER")
ANIMALS = ("GOOSE", "COW", "SHEEP")


def _source_replay(episode_id):
    return json.loads(next(REPLAY_DIR.glob(f"episode-{episode_id}-replay.json")).read_text())


def _recorded_shop_schedule(replay):
    schedule = {}
    for states in replay["steps"]:
        obs = states[0]["observation"]
        schedule.setdefault(int(obs["day"]), list(obs["town"]["unlocked_shops"]))
    return schedule


def _independent_shop_schedule(seed):
    shops = []
    schedule = {0: []}
    for day in range(1, 30):
        if day % 3 == 0 and len(shops) < 8:
            rng = random.Random(((int(seed) * 1_000_003) ^ (day - 1)) ^ 0xA17E)
            shops.append(rng.choice(sorted(game.SHOPS)))
        schedule[day] = list(shops)
    return schedule


def _run_fixed(env, pair, schedule):
    original = game._end_of_day

    def controlled(state, inner_env, day):
        original(state, inner_env, day)
        if day + 1 in schedule:
            state[0].observation.town["unlocked_shops"] = list(schedule[day + 1])

    game._end_of_day = controlled
    try:
        env.run(pair)
    finally:
        game._end_of_day = original


def _percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    point = fraction * (len(values) - 1)
    lo = int(point)
    hi = min(lo + 1, len(values) - 1)
    weight = point - lo
    return values[lo] * (1 - weight) + values[hi] * weight


def _plain(counter):
    return {key: counter[key] for key in sorted(counter) if counter[key]}


def _economics(replay, player):
    windows = {
        "full": (0, 29),
        "day10_20": (10, 20),
        "day20_29": (20, 29),
        "day21_29": (21, 29),
    }
    result = {name: {"revenue": Counter(), "seed_spend": 0, "feed_spend": 0, "animal_spend": 0, "labor_spend": 0, "land_spend": 0, "animal_service": 0} for name in windows}
    errors = []
    for index in range(1, len(replay["steps"])):
        previous, current = replay["steps"][index - 1], replay["steps"][index]
        day = int(previous[0]["observation"]["day"])
        ledgers, mismatch = _transition_ledger(previous, current, replay["configuration"])
        errors.extend(mismatch)
        ledger = ledgers[player]
        for name, (start, end) in windows.items():
            if not start <= day <= end:
                continue
            row = result[name]
            row["revenue"].update(ledger["sale_revenue"])
            row["seed_spend"] += sum(ledger["seed_spend"].values())
            row["feed_spend"] += sum(ledger["product_spend"].values())
            row["animal_spend"] += sum(ledger["animal_spend"].values())
            row["labor_spend"] += ledger["labor_spend"]
            row["land_spend"] += ledger["land_spend"]
            row["animal_service"] += ledger["feed_actions"] + ledger["care_actions"] + ledger["fertilizer_collected"]
    if errors:
        raise AssertionError(errors[:3])
    for row in result.values():
        row["crop_revenue"] = sum(row["revenue"][crop] for crop in CROPS)
        row["animal_revenue"] = sum(row["revenue"][item] for item in ANIMAL_PRODUCTS)
        row["revenue"] = _plain(row["revenue"])
    return result


def _stranded(final_state):
    private = final_state.observation["private"]
    prices = final_state.observation["market"]["prices"]
    value = 0
    for item in SELLABLE:
        quantity = private["shed"].get(item, 0) + sum(inv.get(item, 0) for inv in private["inventories"])
        value += quantity * prices.get(item, 0)
    return value


def _run(job):
    return_replay = len(job) > 8 and bool(job[8])
    candidate, path, group, opponent, spec, seed, seat, schedule = job[:8]
    base = run_path(str(ROOT / path))["agent"]
    rival = _load_opponent(spec)
    calls = 0

    def checked(obs):
        nonlocal calls
        action = base(obs)
        _validate_action(obs, action)
        calls += 1
        return action

    pair = [rival, rival]
    pair[seat] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=True)
    if schedule is None:
        env.run(pair)
    else:
        _run_fixed(env, pair, schedule)
    final = env.steps[-1]
    statuses = [state.status for state in final]
    if len(env.steps) != 720 or statuses != ["DONE", "DONE"] or calls != 719:
        raise RuntimeError((candidate, opponent, seed, seat, len(env.steps), statuses, calls))
    replay = env.toJSON()
    replant_events, ongoing = _event_rows(replay, seat, 10, 25)
    replant = _replant_summary(replant_events, ongoing)
    lifecycle_mid = lifecycle_metrics(replay, seat, 10, 20)
    lifecycle_late = lifecycle_metrics(replay, seat, 21, 29)
    field = _field_analysis(replay, [seat])[seat]
    all_rows = field["daily"]
    rows = all_rows[10:30]
    all_counts = Counter()
    for row in all_rows:
        all_counts.update(row["counts"])
    counts = Counter()
    responsibilities = Counter()
    for row in rows:
        counts.update(row["counts"])
        responsibilities.update(row["responsibilities"])
    economics = _economics(replay, seat)
    bought = Counter()
    for states in replay["steps"][1:]:
        for order in (states[seat].get("action") or {}).get("market", []):
            if isinstance(order, list) and len(order) >= 3 and order[0] == "BUY_ANIMAL":
                bought[order[1]] += int(order[2])
    remaining = Counter()
    farm = final[seat].observation["farms"][seat]
    private = final[seat].observation["private"]
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal"):
                remaining[tile["animal"]] += 1
    for animal in ANIMALS:
        remaining[animal] += private["shed"].get(animal, 0) + sum(inv.get(animal, 0) for inv in private["inventories"])
    money, opponent_money = float(final[seat].reward), float(final[1 - seat].reward)
    result = {
        "candidate": candidate, "path": path, "group": group, "opponent": opponent,
        "seed": int(seed), "seat": seat, "money": money, "opponent_money": opponent_money,
        "advantage": money - opponent_money, "calls": calls,
        "runtime_failures": 0, "semantic_failures": 0,
        "invalid_actions": all_counts["invalid"], "stranded_value": _stranded(final[seat]),
        "livestock_losses": {animal: max(0, bought[animal] - remaining[animal]) for animal in ANIMALS},
        "replant": replant, "replant_events": replant_events,
        "lifecycle_day10_20": lifecycle_mid, "lifecycle_day21_29": lifecycle_late,
        "economics": economics,
        "crop_worker_turns": responsibilities["crop"],
        "animal_service_worker_turns": responsibilities["animal"],
        "movement_actions": counts["movement"], "worker_turns": counts["total"],
    }
    return (result, replay) if return_replay else result


def _summary(games):
    advantages = [row["advantage"] for row in games]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    ties = len(games) - wins - losses
    paired = defaultdict(list)
    for row in games:
        paired[(row["opponent"], row["seed"])].append(row["advantage"])
    mean = lambda fn: statistics.fmean(fn(row) for row in games)
    return {
        "games": len(games), "wins": wins, "losses": losses, "ties": ties,
        "average_money": mean(lambda row: row["money"]),
        "average_advantage": statistics.fmean(advantages),
        "p10_paired_advantage": _percentile([statistics.fmean(v) for v in paired.values()], 0.1),
        "money_stddev": statistics.pstdev(row["money"] for row in games),
        "average_replant_latency": mean(lambda row: row["replant"]["average_delay"] or 0),
        "median_replant_latency": statistics.median(row["replant"]["median_delay"] or 0 for row in games),
        "average_p90_replant_latency": mean(lambda row: row["replant"]["p90_delay"] or 0),
        "average_same_tile_immediate_replant_rate": mean(
            lambda row: row["replant"]["same_tile_immediate_replant_rate"]
        ),
        "average_within_2_turns": mean(lambda row: row["replant"]["within_2_turns"]),
        "average_within_5_turns": mean(lambda row: row["replant"]["within_5_turns"]),
        "average_within_10_turns": mean(lambda row: row["replant"]["within_10_turns"]),
        "average_within_20_turns": mean(lambda row: row["replant"]["within_20_turns"]),
        "average_same_worker_rate": mean(lambda row: row["replant"]["same_worker_rate_reliable_subset"]),
        "seed_related_shed_trips": sum(row["replant"]["seed_related_shed_trips"] for row in games),
        "seed_retrieval_movement": sum(row["replant"]["seed_retrieval_movement"] for row in games),
        "average_crop_harvests_day10_20": mean(lambda row: row["lifecycle_day10_20"]["total_harvest_actions"]),
        "average_crop_harvests_day21_29": mean(lambda row: row["lifecycle_day21_29"]["total_harvest_actions"]),
        "average_strawberry_harvests_day10_20": mean(lambda row: row["lifecycle_day10_20"]["harvest_actions"].get("STRAWBERRY", 0)),
        "average_crop_revenue": mean(lambda row: row["economics"]["full"]["crop_revenue"]),
        "average_animal_revenue": mean(lambda row: row["economics"]["full"]["animal_revenue"]),
        "average_crop_revenue_day10_20": mean(lambda row: row["economics"]["day10_20"]["crop_revenue"]),
        "average_crop_revenue_day21_29": mean(lambda row: row["economics"]["day21_29"]["crop_revenue"]),
        "average_critical_watering_miss_rate": mean(lambda row: row["lifecycle_day10_20"]["critical_watering_miss_rate"]),
        "average_harvest_delay": mean(lambda row: row["lifecycle_day10_20"]["average_harvest_delay_turns"] or 0),
        "average_movement_per_crop_cycle": mean(lambda row: row["lifecycle_day10_20"]["movement_per_crop_cycle"]),
        "average_completed_cycles_per_worker_day": mean(lambda row: row["lifecycle_day10_20"]["completed_cycles_per_worker_day"]),
        "average_productive_tile_hours": mean(lambda row: row["lifecycle_day10_20"]["productive_crop_tile_hours"]),
        "average_crop_worker_turns": mean(lambda row: row["crop_worker_turns"]),
        "average_animal_service_worker_turns": mean(lambda row: row["animal_service_worker_turns"]),
        "total_invalid_actions": sum(row["invalid_actions"] for row in games),
        "total_livestock_losses": sum(sum(row["livestock_losses"].values()) for row in games),
        "max_stranded_value": max(row["stranded_value"] for row in games),
    }


def _candidate_rows(games, candidates):
    controls = {(g["group"], g["opponent"], g["seed"], g["seat"]): g for g in games if g["candidate"] == "P0"}
    output = []
    for candidate in candidates:
        selected = [g for g in games if g["candidate"] == candidate]
        groups = {name: _summary([g for g in selected if g["group"] == name]) for name in sorted({g["group"] for g in selected})}
        matchups = {name: _summary([g for g in selected if g["opponent"] == name]) for name in sorted({g["opponent"] for g in selected})}
        deltas = defaultdict(list)
        for row in selected:
            key = (row["group"], row["opponent"], row["seed"], row["seat"])
            if key in controls:
                deltas[row["group"]].append(row["money"] - controls[key]["money"])
        output.append({
            "candidate": candidate, "path": CANDIDATES[candidate],
            "overall": _summary(selected), "groups": groups, "matchups": matchups,
            "paired_own_money_delta_vs_P0": {name: statistics.fmean(values) for name, values in deltas.items()},
        })
    return output


def _jobs(stage, candidates, seeds):
    jobs = []
    def add(candidate, group, opponent, spec, seed, schedule):
        for seat in (0, 1):
            jobs.append((candidate, CANDIDATES[candidate], group, opponent, spec, seed, seat, schedule))
    if stage == "rng":
        for candidate in candidates:
            for seed in seeds:
                add(candidate, "rng_fixed", "current_fixed", "agents/lifecycle_lc_combined.py", seed, _independent_shop_schedule(seed))
                add(candidate, "rng_natural", "current_natural", "agents/lifecycle_lc_combined.py", seed, None)
        return jobs
    if stage in {"real", "cow"}:
        for candidate in candidates:
            for episode in LOSS_EPISODES:
                replay = _source_replay(episode)
                add(candidate, "real_losses", REAL_NAMES[episode], _trace_spec(episode), int(replay["info"]["seed"]), _recorded_shop_schedule(replay))
        return jobs
    if stage == "redteam":
        for candidate in candidates:
            for opponent, spec in HARD_POOL.items():
                for seed in seeds[:2]:
                    add(candidate, "hard_pool", opponent, spec, seed, _independent_shop_schedule(seed))
            for seed in seeds[:8]:
                add(candidate, "direct", "current_best", "agents/lifecycle_lc_combined.py", seed, _independent_shop_schedule(seed))
        return jobs
    if stage == "confirmation":
        for candidate in candidates:
            for episode in LOSS_EPISODES:
                replay = _source_replay(episode)
                add(candidate, "real_losses", REAL_NAMES[episode], _trace_spec(episode), int(replay["info"]["seed"]), _recorded_shop_schedule(replay))
            for seed in seeds[:8]:
                add(candidate, "direct", "current_best", "agents/lifecycle_lc_combined.py", seed, _independent_shop_schedule(seed))
            for opponent, spec in HARD_POOL.items():
                add(candidate, "hard_pool", opponent, spec, seeds[0], _independent_shop_schedule(seeds[0]))
        return jobs
    real = (92008833, 92010768) if stage == "screen" else LOSS_EPISODES
    for candidate in candidates:
        for episode in real:
            replay = _source_replay(episode)
            group = "jay_pedro" if episode in {92008833, 92010768} else "real_losses"
            add(candidate, group, REAL_NAMES[episode], _trace_spec(episode), int(replay["info"]["seed"]), _recorded_shop_schedule(replay))
        if stage in {"selection", "heldout"}:
            n = 3 if stage == "selection" else 8
            for seed in seeds[:n]:
                add(candidate, "direct", "current_best", "agents/lifecycle_lc_combined.py", seed, _independent_shop_schedule(seed))
            pool = REPLAY_DERIVED if stage == "selection" else HARD_POOL
            n_pool = 1 if stage == "selection" else 3
            for opponent, spec in pool.items():
                for seed in seeds[:n_pool]:
                    add(candidate, "replay_pool" if opponent in REPLAY_DERIVED else "hard_pool", opponent, spec, seed, _independent_shop_schedule(seed))
    return jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("screen", "real", "cow", "selection", "heldout", "redteam", "confirmation", "rng"), default="screen")
    parser.add_argument("--candidates", default="P0,P1_seed_semantic_control,P2_predictive,P3_safe_chain,P3b_recent_empty,P4_cohort,P5_combined")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--seed-start", type=int, default=952000)
    parser.add_argument("--output")
    args = parser.parse_args()
    candidates = tuple(value for value in args.candidates.split(",") if value)
    for candidate in candidates:
        if candidate not in CANDIDATES or not (ROOT / CANDIDATES[candidate]).exists():
            raise FileNotFoundError(candidate)
    seeds = tuple(range(args.seed_start, args.seed_start + 8))
    jobs = _jobs(args.stage, candidates, seeds)
    games = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(_run, job) for job in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 24 == 0 or index == len(jobs):
                print(f"{args.stage}: {index}/{len(jobs)}", flush=True)
    payload = {
        "schema_version": 1, "stage": args.stage,
        "shop_control": "recorded/fixed except explicit natural-RNG audit",
        "candidates": _candidate_rows(games, candidates), "games": games,
    }
    output = Path(args.output) if args.output else ROOT / "experiments" / f"replant_pipeline_{args.stage}.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(output)
    for row in payload["candidates"]:
        s = row["overall"]
        print(row["candidate"], f"{s['wins']}/{s['losses']}/{s['ties']}", f"money={s['average_money']:.0f}", f"adv={s['average_advantage']:+.0f}", f"replant={s['average_replant_latency']:.2f}", f"p90={s['average_p90_replant_latency']:.1f}", f"<=2={s['average_within_2_turns']:.1%}", f"harvest={s['average_crop_harvests_day10_20'] + s['average_crop_harvests_day21_29']:.1f}", f"crop={s['average_crop_revenue']:.0f}", f"crit={s['average_critical_watering_miss_rate']:.2%}")


if __name__ == "__main__":
    main()
