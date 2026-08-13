"""Controlled day-10–20 crop lifecycle scheduler ablations."""

from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from runpy import run_path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as game

from analyze_crop_lifecycle import lifecycle_metrics
from analyze_post_opening_real_gap import _field_analysis
from analyze_top_player_replays import _transition_ledger
from run_post_opening_validation import LOSS_EPISODES, REPLAY_DERIVED, REPLAY_DIR, ROOT, _load_opponent, _trace_spec
from test_economic_agents import SELLABLE, _validate_action


CANDIDATES = {
    "L0_current": "agents/opening_public_front_cow8_day6.py",
    "T2_deploy": "agents/post_opening_t2_deploy.py",
    "L1_deadline_water": "agents/lifecycle_l1_deadline_water.py",
    "L1b_deadline_rescue": "agents/lifecycle_l1b_deadline_rescue.py",
    "L2_ready_harvest": "agents/lifecycle_l2_ready_harvest.py",
    "L3_safe_chain": "agents/lifecycle_l3_safe_chain.py",
    "L4_admission": "agents/lifecycle_l4_admission.py",
    "L5_workload_territory": "agents/lifecycle_l5_workload_territory.py",
    "L6_cohort_priority": "agents/lifecycle_l6_cohort_priority.py",
    "LC_combined": "agents/lifecycle_lc_combined.py",
    "LCD_deadline_combined": "agents/lifecycle_lcd_deadline_combined.py",
}
CONFIRM_OPPONENTS = {
    "current_direct": "agents/opening_public_front_cow8_day6.py",
    **REPLAY_DERIVED,
    "livestock_crop": "agents/proxies/livestock_crop.py",
    "high_labor": "agents/proxies/high_labor.py",
    "phased_rotation": "agents/proxies/phased_rotation.py",
    "gen_cow6_d8": "agents/adversaries/gen_cow6_d8.py",
}
CROPS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
ANIMAL_PRODUCTS = ("EGG", "MILK", "WOOL", "FERTILIZER")


def _source_replay(episode_id):
    return json.loads(next(REPLAY_DIR.glob(f"episode-{episode_id}-replay.json")).read_text())


def _recorded_shop_schedule(replay):
    schedule = {}
    for states in replay["steps"]:
        obs = states[0]["observation"]
        day = int(obs["day"])
        schedule.setdefault(day, list(obs["town"]["unlocked_shops"]))
    return schedule


def _independent_shop_schedule(seed):
    shops = []
    schedule = {0: []}
    for day in range(1, 30):
        if day % 3 == 0 and len(shops) < 8:
            rng = random.Random(((int(seed) * 1_000_003) ^ (day - 1)) ^ 0x5A17C9)
            shops.append(rng.choice(sorted(game.SHOPS)))
        schedule[day] = list(shops)
    return schedule


def _run_with_fixed_shops(env, pair, schedule):
    original = game._end_of_day

    def controlled(state, inner_env, day):
        original(state, inner_env, day)
        next_day = day + 1
        if next_day in schedule:
            state[0].observation.town["unlocked_shops"] = list(schedule[next_day])

    game._end_of_day = controlled
    try:
        env.run(pair)
    finally:
        game._end_of_day = original


def _economics(replay, player, start_day=10, end_day=20):
    sales = Counter()
    revenue = Counter()
    harvest_units = Counter()
    for index in range(1, len(replay["steps"])):
        previous = replay["steps"][index - 1]
        current = replay["steps"][index]
        day = int(previous[0]["observation"]["day"])
        if not start_day <= day <= end_day:
            continue
        ledgers, errors = _transition_ledger(previous, current, replay["configuration"])
        if errors:
            raise AssertionError(errors[:3])
        ledger = ledgers[player]
        sales.update(ledger["sale_quantity"])
        revenue.update(ledger["sale_revenue"])
        harvest_units.update(ledger["harvest_quantity"])
    return {
        "sales": dict(sales),
        "sale_revenue": dict(revenue),
        "harvest_units": dict(harvest_units),
        "crop_revenue": sum(revenue[crop] for crop in CROPS),
        "animal_revenue": sum(revenue[product] for product in ANIMAL_PRODUCTS),
        "weighted_sale_prices": {
            product: revenue[product] / quantity
            for product, quantity in sales.items() if quantity
        },
    }


def _stranded(state):
    private = state.observation["private"]
    return sum(private["shed"].get(item, 0) for item in SELLABLE) + sum(
        inventory.get(item, 0)
        for inventory in private["inventories"]
        for item in SELLABLE
    )


def _run(job):
    candidate, candidate_path, group, opponent, opponent_spec, seed, seat, shop_schedule = job
    base = run_path(str(ROOT / candidate_path))["agent"]
    rival = _load_opponent(opponent_spec)
    calls = 0

    def checked(obs):
        nonlocal calls
        action = base(obs)
        _validate_action(obs, action)
        calls += 1
        return action

    pair = [rival, rival]
    pair[seat] = checked
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": 720, "seed": int(seed)},
        debug=True,
    )
    _run_with_fixed_shops(env, pair, shop_schedule)
    final = env.steps[-1]
    statuses = [state.status for state in final]
    if len(env.steps) != 720 or statuses != ["DONE", "DONE"] or calls != 719:
        raise RuntimeError((candidate, opponent, seed, seat, len(env.steps), statuses, calls))
    replay = env.toJSON()
    lifecycle = lifecycle_metrics(replay, seat)
    economics = _economics(replay, seat)
    routing = _field_analysis(replay, [seat])[seat]
    invalid = sum(
        row["counts"].get("invalid", 0) for row in routing["daily"][10:21]
    )
    all_harvests = sum(
        row["counts"].get("successful_HARVEST", 0)
        for row in routing["daily"][10:21]
    )
    money = float(final[seat].reward)
    opponent_money = float(final[1 - seat].reward)
    return {
        "candidate": candidate,
        "path": candidate_path,
        "group": group,
        "opponent": opponent,
        "seed": seed,
        "seat": seat,
        "money": money,
        "opponent_money": opponent_money,
        "advantage": money - opponent_money,
        "stranded": _stranded(final[seat]),
        "semantic_failures": 0,
        "runtime_failures": 0,
        "invalid_field_actions_day10_20": invalid,
        "all_successful_harvests_day10_20": all_harvests,
        "economics": economics,
        "lifecycle": lifecycle,
        "shop_schedule": shop_schedule,
    }


def _percentile(values, fraction):
    ordered = sorted(values)
    point = fraction * (len(ordered) - 1)
    lower = int(point)
    upper = min(lower + 1, len(ordered) - 1)
    weight = point - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _summary(games):
    advantages = [row["advantage"] for row in games]
    wins = sum(value > 0 for value in advantages)
    losses = sum(value < 0 for value in advantages)
    ties = len(games) - wins - losses
    paired = {}
    for row in games:
        paired.setdefault((row["opponent"], row["seed"]), []).append(row["advantage"])
    harvest_actions = {
        crop: statistics.fmean(row["lifecycle"]["harvest_actions"].get(crop, 0) for row in games)
        for crop in CROPS
    }
    harvest_units = {
        crop: statistics.fmean(row["lifecycle"]["harvest_units"].get(crop, 0) for row in games)
        for crop in CROPS
    }
    return {
        "games": len(games),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "score_rate": (wins + 0.5 * ties) / len(games),
        "average_money": statistics.fmean(row["money"] for row in games),
        "average_advantage": statistics.fmean(advantages),
        "p10_paired_advantage": _percentile(
            [statistics.fmean(values) for values in paired.values()], 0.10
        ),
        "harvest_actions_by_crop": harvest_actions,
        "harvest_units_by_crop": harvest_units,
        "average_total_crop_harvest_actions": statistics.fmean(
            row["lifecycle"]["total_harvest_actions"] for row in games
        ),
        "average_total_crop_harvest_units": statistics.fmean(
            row["lifecycle"]["total_harvest_units"] for row in games
        ),
        "average_all_successful_harvests_day10_20": statistics.fmean(
            row["all_successful_harvests_day10_20"] for row in games
        ),
        "average_crop_revenue_day10_20": statistics.fmean(
            row["economics"]["crop_revenue"] for row in games
        ),
        "average_watering_miss_rate": statistics.fmean(
            row["lifecycle"]["watering_miss_rate"] for row in games
        ),
        "average_critical_watering_miss_rate": statistics.fmean(
            row["lifecycle"]["critical_watering_miss_rate"] for row in games
        ),
        "average_harvest_delay_turns": statistics.fmean(
            row["lifecycle"]["average_harvest_delay_turns"] for row in games
        ),
        "average_replant_delay_turns": statistics.fmean(
            row["lifecycle"]["average_replant_delay_turns"] for row in games
        ),
        "average_movement_per_crop_cycle": statistics.fmean(
            row["lifecycle"]["movement_per_crop_cycle"] for row in games
        ),
        "average_lifecycle_debt_tile_hours": statistics.fmean(
            row["lifecycle"]["lifecycle_debt_tile_hours"] for row in games
        ),
        "average_productive_crop_tile_hours": statistics.fmean(
            row["lifecycle"]["productive_crop_tile_hours"] for row in games
        ),
        "average_completed_cycles_per_worker_day": statistics.fmean(
            row["lifecycle"]["completed_cycles_per_worker_day"] for row in games
        ),
        "average_lost_crops": statistics.fmean(
            sum(row["lifecycle"]["lost_crops"].values()) for row in games
        ),
        "total_invalid_field_actions_day10_20": sum(
            row["invalid_field_actions_day10_20"] for row in games
        ),
        "max_stranded": max(row["stranded"] for row in games),
    }


def _rows(games, candidates, groups):
    result = []
    for candidate in candidates:
        selected = [row for row in games if row["candidate"] == candidate]
        matchups = {
            opponent: _summary([row for row in selected if row["opponent"] == opponent])
            for opponent in sorted({row["opponent"] for row in selected})
        }
        result.append({
            "candidate": candidate,
            "path": CANDIDATES[candidate],
            "overall": _summary(selected),
            "groups": {
                group: _summary([row for row in selected if row["group"] == group])
                for group in groups
            },
            "matchups": matchups,
        })
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("screen", "confirm"), default="screen")
    parser.add_argument("--candidates", default="L0_current,L1_deadline_water,L2_ready_harvest,L3_safe_chain,L4_admission,L5_workload_territory,L6_cohort_priority")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--seeds", type=int, default=8)
    parser.add_argument("--output")
    args = parser.parse_args()
    candidates = tuple(value for value in args.candidates.split(",") if value)
    for candidate in candidates:
        if not (ROOT / CANDIDATES[candidate]).exists():
            raise FileNotFoundError(CANDIDATES[candidate])

    jobs = []
    groups = set()
    if args.stage == "screen":
        groups.add("reconstructed_real_losses")
        for candidate in candidates:
            for episode_id in LOSS_EPISODES:
                source = _source_replay(episode_id)
                seed = int(source["info"]["seed"])
                schedule = _recorded_shop_schedule(source)
                spec = _trace_spec(episode_id)
                for seat in (0, 1):
                    jobs.append((
                        candidate, CANDIDATES[candidate], "reconstructed_real_losses",
                        f"episode_{episode_id}", spec, seed, seat, schedule,
                    ))
    else:
        seeds = tuple(range(825000, 825000 + args.seeds))
        groups.update(("fresh_direct", "fresh_replay_league", "reconstructed_real_losses"))
        for candidate in candidates:
            for opponent, path in CONFIRM_OPPONENTS.items():
                group = "fresh_direct" if opponent == "current_direct" else "fresh_replay_league"
                for seed in seeds:
                    schedule = _independent_shop_schedule(seed)
                    for seat in (0, 1):
                        jobs.append((
                            candidate, CANDIDATES[candidate], group,
                            opponent, path, seed, seat, schedule,
                        ))
            for episode_id in LOSS_EPISODES:
                source = _source_replay(episode_id)
                seed = int(source["info"]["seed"])
                schedule = _recorded_shop_schedule(source)
                spec = _trace_spec(episode_id)
                for seat in (0, 1):
                    jobs.append((
                        candidate, CANDIDATES[candidate], "reconstructed_real_losses",
                        f"episode_{episode_id}", spec, seed, seat, schedule,
                    ))

    games = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(_run, job) for job in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 24 == 0 or index == len(jobs):
                print(f"{args.stage}: {index}/{len(jobs)}", flush=True)
    payload = {
        "schema_version": 1,
        "stage": args.stage,
        "fixed_economic_policy": "agents/opening_public_front_cow8_day6.py",
        "opening_unchanged_through_day": 10,
        "shop_control": (
            "recorded shop schedule for replay losses; independently seeded common schedule for fresh games"
        ),
        "candidate_names": list(candidates),
        "candidates": _rows(games, candidates, sorted(groups)),
        "games": games,
    }
    output = ROOT / args.output if args.output else ROOT / "experiments" / f"crop_lifecycle_{args.stage}.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(output)
    for row in payload["candidates"]:
        s = row["overall"]
        print(
            row["candidate"], f"{s['wins']}/{s['losses']}/{s['ties']}",
            f"money={s['average_money']:.0f}", f"adv={s['average_advantage']:+.0f}",
            f"harvests={s['average_total_crop_harvest_actions']:.1f}",
            f"crop_rev={s['average_crop_revenue_day10_20']:.0f}",
            f"critical={s['average_critical_watering_miss_rate']:.2%}",
            f"hdelay={s['average_harvest_delay_turns']:.1f}",
            f"rdelay={s['average_replant_delay_turns']:.1f}",
            f"debt={s['average_lifecycle_debt_tile_hours']:.0f}",
        )


if __name__ == "__main__":
    main()
