"""Evaluate the S0--S3 crop lifecycle scheduler ablations.

The benchmark keeps the frozen Top-50 portfolio as the economic control and
changes only farmer/hand actions.  It writes a machine-readable replay
ledger plus a compact Markdown report under ``experiments/``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
import math
from pathlib import Path
import statistics
from runpy import run_path

from kaggle_environments import make

from run_epic_experiments import _independent_shop_schedule, _recorded_shop_schedule
from run_leaderboard_breakthrough import REPLAY_CASES
from run_post_opening_validation import _load_opponent
from run_v27_replay_backbone import _inventory_value, _semantic_validate
from analyze_top_player_replays import _transition_ledger


ROOT = Path(__file__).resolve().parent
EPISODE_STEPS = 720
CANDIDATES = {
    "S0_currentbest": "agents/territory_s0_currentbest.py",
    "S1_persistent": "agents/territory_s1_persistent.py",
    "S2_deadline": "agents/territory_s2_deadline.py",
    "S3_chain": "agents/territory_s3_chain.py",
}
REAL_CASES = {
    key: REPLAY_CASES[key]
    for key in (
        "Jayveer_melon_burst",
        "Pedro_wheat_turnover",
        "Lucas_four_quadrant",
        "Alexander_cow_melon",
    )
}
PROXIES = {
    "proxy_livestock_crop": "agents/proxies/livestock_crop.py",
    "proxy_high_labor": "agents/proxies/high_labor.py",
    "proxy_land_expander": "agents/proxies/land_expander.py",
    "proxy_phased_rotation": "agents/proxies/phased_rotation.py",
    "router_replay_hands12": "agents/router_replay_hands12.py",
    # Complete high-rating route families are included as stronger local
    # controls than the intentionally simple archetype proxies above.
    "top50_dmitry": "agents/top50_distilled/top50_dmitry_safe.py",
    "top50_hanserong": "agents/top50_distilled/top50_hanserong_safe.py",
    "top50_redblack": "agents/top50_distilled/top50_redblack_safe.py",
    "super_replay_v2": "agents/super_replay_v2/super_backbone_v2.py",
    "v27_k9_full": "agents/v27_k9_full.py",
    "lifecycle_lc": "agents/lifecycle_lc_combined.py",
}
CROPS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}
ANIMALS = {"GOOSE", "COW", "SHEEP"}
PRODUCTS = CROPS | {"EGG", "MILK", "WOOL", "FERTILIZER"}
UNIT_OPS = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER", "HARVEST",
    "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "PICKUP", "DROP",
    "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER",
}
MARKET_OPS = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}
_CROP_DATA = run_path(str(ROOT / "agents" / "animal_land_common.py"))["CROPS"]


def _trace_spec(path, player):
    return f"trace:{ROOT / path}:{int(player)}"


def _percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    point = fraction * (len(values) - 1)
    lower = int(point)
    upper = min(lower + 1, len(values) - 1)
    weight = point - lower
    return values[lower] * (1.0 - weight) + values[upper] * weight


def _validate(obs, action):
    _semantic_validate(obs, action)
    if set(action) != {"farmer", "hands", "market"}:
        raise AssertionError("action must contain farmer/hands/market only")
    for field in (action["farmer"], *action["hands"]):
        if field[0] not in UNIT_OPS:
            raise AssertionError(f"invalid unit op {field}")
    for order in action["market"]:
        if order[0] not in MARKET_OPS:
            raise AssertionError(f"invalid market op {order}")


def _farm_animals(obs, player):
    counts = Counter()
    farm = obs["farms"][player]
    for row in farm["tiles"]:
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal") in ANIMALS:
                counts[tile["animal"]] += 1
    private = obs.get("private", {})
    counts.update({animal: int(private.get("shed", {}).get(animal, 0)) for animal in ANIMALS})
    for inventory in private.get("inventories", []):
        counts.update({animal: int(inventory.get(animal, 0)) for animal in ANIMALS})
    return counts


def _economic_metrics(replay, seat):
    """Reconstruct lifecycle, sales, and workload metrics from one replay."""
    steps = replay["steps"]
    configuration = replay.get("configuration", {})
    totals = Counter()
    by_day = defaultdict(Counter)
    crop_harvests = Counter()
    crop_sales = Counter()
    sale_revenue = Counter()
    watering_checks = 0
    watering_misses = 0
    critical_misses = 0
    productive_tile_hours = 0
    worker_actions = 0
    worker_days = set()
    harvest_delays = []
    replant_delays = []
    cycle_move_distances = []
    last_harvest_at = {}
    last_harvest_worker = {}
    animal_bought = Counter()

    for index in range(1, len(steps)):
        previous = steps[index - 1]
        current = steps[index]
        prev_obs = previous[seat]["observation"]
        obs = current[seat]["observation"]
        day = int(prev_obs.get("day", prev_obs.get("step", 0) // 24))
        hour = int(prev_obs.get("hour", prev_obs.get("step", 0) % 24))
        action = current[seat].get("action") or {}
        fields = [action.get("farmer", ["PASS"]), *list(action.get("hands", []))]
        positions = [tuple(prev_obs["farms"][seat]["farmer"]), *[
            tuple(p) for p in prev_obs["farms"][seat].get("hands", [])
        ]]
        worker_actions += len(fields)
        for unit_index in range(len(positions)):
            worker_days.add((day, unit_index))
            field = fields[unit_index] if unit_index < len(fields) else ["PASS"]
            op = field[0] if isinstance(field, list) and field else "PASS"
            if op in {"NORTH", "SOUTH", "EAST", "WEST", "PASS"}:
                continue
            position = positions[unit_index]
            tile = prev_obs["farms"][seat]["tiles"][position[1]][position[0]]
            if op == "HARVEST" and isinstance(tile, dict) and tile.get("kind") == "PLANT":
                crop = tile.get("crop")
                if crop in CROPS:
                    crop_harvests[crop] += 1
                    data = _CROP_DATA.get(crop, {})
                    age = day - int(tile.get("planted_day", day))
                    peak = int(data.get("peak", data.get("max_yield_day", data.get("first", 0))))
                    harvest_delays.append(max(0, age - peak))
                    last_harvest_at[position] = int(prev_obs.get("step", index - 1))
                    last_harvest_worker[position] = (day, unit_index, positions[unit_index])
            elif op == "PLANT" and len(field) >= 2 and tile is None:
                crop = field[1]
                if crop in CROPS and position in last_harvest_at:
                    delay = int(prev_obs.get("step", index - 1)) - last_harvest_at[position]
                    replant_delays.append(max(0, delay))
                    prior = last_harvest_worker.get(position)
                    if prior and prior[1] == unit_index:
                        cycle_move_distances.append(
                            abs(position[0] - prior[2][0]) + abs(position[1] - prior[2][1])
                        )
        if hour == int(configuration.get("turnsPerDay", 24)) - 1:
            # At the next observation, refresh has already reset watered_today;
            # consecutive_unwatered therefore identifies missed maintenance.
            next_farm = obs["farms"][seat]
            for row in next_farm["tiles"]:
                for tile in row:
                    if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                        watering_checks += 1
                        misses = int(tile.get("consecutive_unwatered", 0)) > 0
                        watering_misses += misses
                        critical_misses += int(tile.get("consecutive_unwatered", 0)) >= 1
                    if isinstance(tile, dict) and (tile.get("kind") == "PLANT" or tile.get("animal")):
                        productive_tile_hours += 1

        try:
            ledgers, _ = _transition_ledger(previous, current, configuration)
        except Exception:
            ledgers = None
        if ledgers:
            ledger = ledgers[seat]
            totals["harvest_units"] += sum(ledger["harvest_quantity"].values())
            totals["plant_actions"] += sum(ledger["plant_quantity"].values())
            for crop, quantity in ledger["harvest_quantity"].items():
                if crop in CROPS:
                    by_day[day]["harvest_units"] += quantity
            for item, quantity in ledger["sale_quantity"].items():
                crop_sales[item] += quantity
            sale_revenue.update(ledger["sale_revenue"])
            animal_bought.update(ledger["animal_quantity"])
            for key in ("seed_spend", "product_spend", "animal_spend"):
                totals[key] += sum(ledger[key].values())
            totals["labor_spend"] += ledger["labor_spend"]
            totals["land_spend"] += ledger["land_spend"]
            if 10 <= day <= 20:
                by_day[day]["crop_revenue"] += sum(
                    value for item, value in ledger["sale_revenue"].items() if item in CROPS
                )

    final_state = steps[-1][seat]
    final_obs = final_state["observation"]
    final_value, stranded = _inventory_value(final_state)
    crop_revenue_10_20 = sum(by_day[day]["crop_revenue"] for day in range(10, 21))
    crop_harvest_10_20 = sum(by_day[day]["harvest_units"] for day in range(10, 21))
    return {
        "harvests_by_crop": dict(crop_harvests),
        "harvest_count": int(sum(crop_harvests.values())),
        "harvest_units": int(totals["harvest_units"]),
        "harvest_count_day10_20": int(crop_harvest_10_20),
        "crop_sales": dict(crop_sales),
        "sale_revenue": dict(sale_revenue),
        "crop_revenue_day10_20": float(crop_revenue_10_20),
        "watering_checks": watering_checks,
        "watering_misses": watering_misses,
        "critical_watering_misses": critical_misses,
        "watering_miss_rate": watering_misses / watering_checks if watering_checks else 0.0,
        "critical_watering_miss_rate": critical_misses / watering_checks if watering_checks else 0.0,
        "harvest_delay_mean": statistics.fmean(harvest_delays) if harvest_delays else 0.0,
        "replant_delay_mean": statistics.fmean(replant_delays) if replant_delays else 0.0,
        "replant_cycles": len(replant_delays),
        "movement_per_cycle": statistics.fmean(cycle_move_distances) if cycle_move_distances else 0.0,
        "productive_tile_hours": productive_tile_hours,
        "worker_actions": worker_actions,
        "worker_days": len(worker_days),
        "cycles_per_worker": len(replant_delays) / max(1, len(worker_days)),
        "spending": dict(totals),
        "animals_bought": dict(animal_bought),
        "final_money": float(final_state["reward"]),
        "opponent_money": float(steps[-1][1 - seat]["reward"]),
        "stranded_value": float(final_value),
        "stranded": stranded,
        "final_animals": dict(_farm_animals(final_obs, seat)),
    }


def _run(job):
    candidate_name, candidate_path, opponent_name, opponent_spec, seed, seat, schedule = job
    candidate = run_path(str(ROOT / candidate_path))["agent"]
    rival = _load_opponent(opponent_spec)
    semantic = []
    runtime_error = None

    def checked(obs):
        action = candidate(obs)
        try:
            _validate(obs, action)
        except Exception as error:
            semantic.append({"step": int(obs.get("step", -1)), "error": repr(error)})
            raise
        return action

    pair = [rival, rival]
    pair[int(seat)] = checked
    env = make("kaggriculture", configuration={"episodeSteps": EPISODE_STEPS, "seed": int(seed)}, debug=True)
    try:
        if schedule is None:
            env.run(pair)
        else:
            # Fixed shop schedules are already represented in the environment
            # helper used by the replay benchmarks; importing lazily avoids a
            # circular import during worker startup.
            from run_epic_experiments import _run_with_fixed_shops
            _run_with_fixed_shops(env, pair, schedule)
    except Exception as error:
        runtime_error = repr(error)
    if runtime_error or len(env.steps) != EPISODE_STEPS:
        return {
            "candidate": candidate_name, "candidate_path": candidate_path,
            "opponent": opponent_name, "seed": int(seed), "seat": int(seat),
            "runtime_error": runtime_error or f"steps={len(env.steps)}",
            "semantic_failures": semantic,
        }
    replay = env.toJSON()
    metrics = _economic_metrics(replay, int(seat))
    bought = Counter(metrics["animals_bought"])
    final_animals = Counter(metrics["final_animals"])
    livestock_losses = sum(max(0, bought[a] - final_animals[a]) for a in ANIMALS)
    metrics.update({
        "candidate": candidate_name, "candidate_path": candidate_path,
        "opponent": opponent_name, "seed": int(seed), "seat": int(seat),
        "advantage": metrics["final_money"] - metrics["opponent_money"],
        "runtime_error": None, "semantic_failures": semantic,
        "livestock_losses": int(livestock_losses),
        "telemetry": deepcopy(getattr(candidate, "telemetry", {})),
    })
    return metrics


def _jobs(candidates, seeds_per_proxy, seed_start=981000, proxy_names=None):
    jobs = []
    # The recorded real-loss traces are a diagnostic primary set.  They use
    # their original deterministic seed and recorded shop schedule.
    for name, (_, replay_path, source_player) in REAL_CASES.items():
        replay = json.loads((ROOT / replay_path).read_text())
        schedule = _recorded_shop_schedule(replay)
        seed = int(replay["info"].get("seed", 0))
        spec = _trace_spec(replay_path, source_player)
        for candidate_name, candidate_path in candidates.items():
            for seat in (0, 1):
                jobs.append((candidate_name, candidate_path, name, spec, seed, seat, schedule))
    # Fresh direct proxy seeds provide held-out pressure and identical shops.
    selected_proxies = PROXIES if proxy_names is None else {
        name: PROXIES[name] for name in proxy_names if name in PROXIES
    }
    for proxy_name, proxy_path in selected_proxies.items():
        for seed in range(int(seed_start), int(seed_start) + seeds_per_proxy):
            schedule = _independent_shop_schedule(seed)
            for candidate_name, candidate_path in candidates.items():
                for seat in (0, 1):
                    jobs.append((candidate_name, candidate_path, proxy_name, proxy_path, seed, seat, schedule))
    return jobs


def _summarize(games, candidates):
    out = {}
    for name in candidates:
        rows = [row for row in games if row.get("candidate") == name and not row.get("runtime_error")]
        advantages = [row["advantage"] for row in rows]
        out[name] = {
            "games": len(rows),
            "wins": sum(value > 0 for value in advantages),
            "losses": sum(value < 0 for value in advantages),
            "ties": sum(value == 0 for value in advantages),
            "win_rate": sum(value > 0 for value in advantages) / max(1, len(rows)),
            "average_money": statistics.fmean(row["final_money"] for row in rows) if rows else 0.0,
            "average_advantage": statistics.fmean(advantages) if advantages else 0.0,
            "median_advantage": statistics.median(advantages) if advantages else 0.0,
            "p10_advantage": _percentile(advantages, 0.10),
            "p5_advantage": _percentile(advantages, 0.05),
            "variance_advantage": statistics.pvariance(advantages) if len(advantages) > 1 else 0.0,
            "runtime_failures": sum(bool(row.get("runtime_error")) for row in games if row.get("candidate") == name),
            "semantic_failures": sum(len(row.get("semantic_failures", [])) for row in games if row.get("candidate") == name),
            "livestock_losses": sum(row.get("livestock_losses", 0) for row in rows),
            "average_harvest_count": statistics.fmean(row["harvest_count"] for row in rows) if rows else 0.0,
            "average_crop_revenue_day10_20": statistics.fmean(row["crop_revenue_day10_20"] for row in rows) if rows else 0.0,
            "average_watering_miss_rate": statistics.fmean(row["watering_miss_rate"] for row in rows) if rows else 0.0,
            "average_replant_delay": statistics.fmean(row["replant_delay_mean"] for row in rows) if rows else 0.0,
            "average_productive_tile_hours": statistics.fmean(row["productive_tile_hours"] for row in rows) if rows else 0.0,
            "average_cycles_per_worker": statistics.fmean(row["cycles_per_worker"] for row in rows) if rows else 0.0,
            "by_opponent": {},
        }
        for opponent in sorted({row.get("opponent") for row in rows}):
            subset = [row for row in rows if row["opponent"] == opponent]
            values = [row["advantage"] for row in subset]
            out[name]["by_opponent"][opponent] = {
                "games": len(subset),
                "wins": sum(value > 0 for value in values),
                "losses": sum(value < 0 for value in values),
                "ties": sum(value == 0 for value in values),
                "average_advantage": statistics.fmean(values) if values else 0.0,
                "p10_advantage": _percentile(values, 0.10),
                "average_money": statistics.fmean(row["final_money"] for row in subset) if subset else 0.0,
            }
    return out


def _write_report(path, payload):
    lines = [
        "# Territory lifecycle scheduler ablation",
        "",
        "The economic program is the frozen Top-50 observable portfolio. Only unit actions differ.",
        f"Seeds per direct proxy: {payload['seeds_per_proxy']}; recorded real-loss cases: {len(REAL_CASES)}; both seats.",
        "",
        "## Aggregate results",
        "",
        "| Candidate | Games | W/L/T | Win rate | Avg money | Avg advantage | Median | P10 | Adv variance | Harvests | Crop rev d10-20 | Water miss | Replant delay | Livestock losses |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, row in payload["summary"].items():
        lines.append(
            f"| {name} | {row['games']} | {row['wins']}/{row['losses']}/{row['ties']} | "
            f"{row['win_rate']*100:.1f}% | {row['average_money']:.1f} | {row['average_advantage']:+.1f} | "
            f"{row['median_advantage']:+.1f} | {row['p10_advantage']:+.1f} | {row['variance_advantage']:.0f} | "
            f"{row['average_harvest_count']:.1f} | {row['average_crop_revenue_day10_20']:.1f} | "
            f"{row['average_watering_miss_rate']*100:.2f}% | {row['average_replant_delay']:.2f} | {row['livestock_losses']} |"
        )
    lines.extend(["", "## Matchups", ""])
    for name, row in payload["summary"].items():
        lines.extend([f"### {name}", "", "| Opponent | Games | W/L/T | Avg advantage | P10 |", "| --- | ---: | ---: | ---: | ---: |"])
        for opponent, matchup in row["by_opponent"].items():
            lines.append(
                f"| {opponent} | {matchup['games']} | {matchup['wins']}/{matchup['losses']}/{matchup['ties']} | "
                f"{matchup['average_advantage']:+.1f} | {matchup['p10_advantage']:+.1f} |"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds-per-proxy", type=int, default=2)
    parser.add_argument("--seed-start", type=int, default=981000)
    parser.add_argument("--proxies", default="")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--candidate", action="append")
    parser.add_argument("--output", default="experiments/territory_lifecycle_ablation.json")
    parser.add_argument("--report", default="experiments/territory_lifecycle_ablation.md")
    args = parser.parse_args()
    candidates = CANDIDATES
    if args.candidate:
        unknown = sorted(set(args.candidate) - set(CANDIDATES))
        if unknown:
            raise SystemExit(f"unknown candidates: {unknown}")
        candidates = {name: CANDIDATES[name] for name in args.candidate}
    proxy_names = [value for value in args.proxies.split(",") if value] or None
    jobs = _jobs(candidates, args.seeds_per_proxy, args.seed_start, proxy_names)
    games = []
    print(f"running {len(jobs)} games", flush=True)
    if args.workers <= 1:
        for index, job in enumerate(jobs, 1):
            games.append(_run(job))
            if index % 10 == 0 or index == len(jobs):
                print(f"completed {index}/{len(jobs)}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(_run, job) for job in jobs]
            for index, future in enumerate(as_completed(futures), 1):
                games.append(future.result())
                if index % 20 == 0 or index == len(jobs):
                    print(f"completed {index}/{len(jobs)}", flush=True)
    games.sort(key=lambda row: (row.get("candidate", ""), row.get("opponent", ""), row.get("seed", 0), row.get("seat", 0)))
    payload = {
        "schema_version": 1,
        "experiment": "currentbest territory lifecycle S0-S3 ablation",
        "current_best": "agents/top50_distilled/top50_observable_portfolio.py",
        "candidates": candidates,
        "opponents": {**{name: "recorded_trace" for name in REAL_CASES}, **PROXIES},
        "real_cases": REAL_CASES,
        "seeds_per_proxy": args.seeds_per_proxy,
        "seed_start": args.seed_start,
        "selected_proxies": proxy_names or list(PROXIES),
        "both_seats": True,
        "games": games,
        "summary": _summarize(games, candidates),
    }
    output = ROOT / args.output
    report = ROOT / args.report
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _write_report(report, payload)
    print(f"saved {output}")
    print(f"saved {report}")
    for name, row in payload["summary"].items():
        print(name, row["wins"], row["losses"], row["ties"], round(row["average_advantage"], 1), round(row["p10_advantage"], 1), row["runtime_failures"], row["semantic_failures"])


if __name__ == "__main__":
    main()
