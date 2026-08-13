"""Replay-grounded post-opening ablations with separately reported leagues."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from analyze_post_opening_real_gap import _field_analysis
from analyze_top_player_replays import _transition_ledger
from test_economic_agents import SELLABLE, _validate_action


ROOT = Path(__file__).resolve().parent
EPISODE_STEPS = 720
CROPS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}
ANIMAL_PRODUCTS = {"EGG", "MILK", "WOOL", "FERTILIZER"}
CANDIDATES = {
    "T0_current": "agents/opening_public_front_cow8_day6.py",
    "T1_hands14": "agents/post_opening_t1_hands14.py",
    "T2_deploy": "agents/post_opening_t2_deploy.py",
    "T3_territory": "agents/post_opening_t3_territory.py",
    "T4_crop_mix": "agents/post_opening_t4_crop_mix.py",
    "F_fertilizer": "agents/post_opening_f_fertilizer.py",
    "W_water_guard": "agents/post_opening_w_water_guard.py",
    "T5_combined": "agents/post_opening_t5_deploy_crop.py",
}
OLD_SYNTHETIC = {
    "livestock_crop": "agents/proxies/livestock_crop.py",
    "high_labor": "agents/proxies/high_labor.py",
    "land_expander": "agents/proxies/land_expander.py",
    "phased_rotation": "agents/proxies/phased_rotation.py",
    "mixed_crop": "agents/proxies/mixed_crop.py",
    "gen_cow6_d8": "agents/adversaries/gen_cow6_d8.py",
}
REPLAY_DERIVED = {
    "aggressive_strawberry": "agents/replay_archetypes/aggressive_strawberry_scaler.py",
    "early_supply_dump": "agents/replay_archetypes/early_supply_dump.py",
    "fast_land_high_labor": "agents/replay_archetypes/fast_land_high_labor.py",
    "livestock_heavy": "agents/replay_archetypes/livestock_heavy_scaler.py",
    "rapid_reinvestment": "agents/replay_archetypes/rapid_sell_reinvestment.py",
    "top_meta_mixed": "agents/router_meta_mixed_throughout.py",
    "top_meta_sheep_cow": "agents/router_meta_sheep_to_cow.py",
}
LOSS_EPISODES = (92008833, 92009080, 92010768, 92011750)
REPLAY_DIR = ROOT / "experiments" / "kaggle_episodes" / "submission_55435253" / "replays"


def _load_agent(path):
    return run_path(str(ROOT / path))["agent"]


def _trace_spec(episode_id):
    path = next(REPLAY_DIR.glob(f"episode-{episode_id}-replay.json"))
    replay = json.loads(path.read_text())
    manifest = json.loads(
        (ROOT / "experiments" / "kaggle_episodes" / "submission_55435253" / "manifest.json").read_text()
    )
    row = next(value for value in manifest["episodes"] if int(value["episode_id"]) == episode_id)
    our_seat = int(row["player"])
    return f"trace:{path}:{1 - our_seat}"


def _load_opponent(spec):
    if not spec.startswith("trace:"):
        return _load_agent(spec)
    _, raw_path, raw_player = spec.split(":", 2)
    replay = json.loads(Path(raw_path).read_text())
    player = int(raw_player)

    def trace_agent(obs):
        source_index = min(int(obs["step"]) + 1, len(replay["steps"]) - 1)
        action = deepcopy(replay["steps"][source_index][player].get("action") or {})
        action.setdefault("farmer", ["PASS"])
        action.setdefault("market", [])
        hands = list(action.get("hands", []))
        desired = len(obs["farms"][obs["player"]].get("hands", []))
        hands.extend([["PASS"]] * max(0, desired - len(hands)))
        action["hands"] = hands[:desired]
        return action

    return trace_agent


def _stranded(final_state):
    private = final_state.observation["private"]
    return sum(private["shed"].get(item, 0) for item in SELLABLE) + sum(
        inventory.get(item, 0)
        for inventory in private["inventories"]
        for item in SELLABLE
    )


def _run(job):
    candidate, candidate_path, group, opponent, opponent_spec, seed, seat = job
    base = _load_agent(candidate_path)
    rival = _load_opponent(opponent_spec)

    def checked(obs):
        action = base(obs)
        _validate_action(obs, action)
        return action

    pair = [rival, rival]
    pair[seat] = checked
    env = make(
        "kaggriculture",
        configuration={"episodeSteps": EPISODE_STEPS, "seed": int(seed)},
        debug=True,
    )
    env.run(pair)
    final = env.steps[-1]
    statuses = [state.status for state in final]
    if len(env.steps) != EPISODE_STEPS or statuses != ["DONE", "DONE"]:
        raise RuntimeError(
            f"failed {candidate}/{group}/{opponent}/{seed}/seat{seat}: "
            f"steps={len(env.steps)} statuses={statuses}"
        )
    replay = env.toJSON()
    routing = _field_analysis(replay, [seat])[seat]
    sales_by_day = [Counter() for _ in range(30)]
    mismatches = []
    for step in range(1, len(replay["steps"])):
        previous = replay["steps"][step - 1]
        current = replay["steps"][step]
        ledgers, errors = _transition_ledger(previous, current, replay["configuration"])
        mismatches.extend(errors)
        day = min(29, int(previous[0]["observation"]["day"]))
        sales_by_day[day].update(ledgers[seat]["sale_revenue"])
    if mismatches:
        raise AssertionError(f"financial mismatches: {mismatches[:3]}")

    rows = routing["daily"][10:21]
    counts = Counter()
    for row in rows:
        counts.update(row["counts"])
    window_sales = sum((sales_by_day[day] for day in range(11, 21)), Counter())
    land = routing["land_events"]
    second = land[1] if len(land) > 1 else {}
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
        "day10_20_revenue": sum(window_sales.values()),
        "day10_20_crop_revenue": sum(window_sales[crop] for crop in CROPS),
        "day10_20_animal_revenue": sum(window_sales[item] for item in ANIMAL_PRODUCTS),
        "average_productive_tiles_day10_20": statistics.fmean(
            row["end_snapshot"]["productive_tiles"] for row in rows
        ),
        "average_capacity_utilization_day10_20": statistics.fmean(
            row["end_snapshot"]["capacity_utilization"] for row in rows
        ),
        "average_utilized_tiles_day10_20": statistics.fmean(
            row["actually_utilized_tiles"] for row in rows
        ),
        "average_hands_day10_20": statistics.fmean(row["max_hands"] for row in rows),
        "movement_ratio_day10_20": counts["movement"] / max(1, counts["total"]),
        "productive_ratio_day10_20": counts["productive"] / max(1, counts["total"]),
        "movement_per_productive_day10_20": counts["movement"] / max(1, counts["productive"]),
        "critical_watering_miss_rate_day10_20": sum(
            row["critical_missed_watering"] for row in rows
        ) / max(1, sum(row["plant_checks"] for row in rows)),
        "fertilize_actions_day10_20": sum(
            row["counts"].get("successful_FERTILIZE", 0) for row in rows
        ),
        "turns_to_23_after_second_land": second.get("turns_to_23_productive"),
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
    numeric = (
        "money", "advantage", "day10_20_revenue", "day10_20_crop_revenue",
        "day10_20_animal_revenue", "average_productive_tiles_day10_20",
        "average_capacity_utilization_day10_20", "average_utilized_tiles_day10_20",
        "average_hands_day10_20", "movement_ratio_day10_20",
        "productive_ratio_day10_20", "movement_per_productive_day10_20",
        "critical_watering_miss_rate_day10_20", "fertilize_actions_day10_20",
    )
    output = {
        "games": len(games), "wins": wins, "losses": losses, "ties": ties,
        "score_rate": (wins + 0.5 * ties) / len(games),
        "p10_paired_advantage": _percentile(
            [statistics.fmean(values) for values in paired.values()], 0.10
        ),
        "max_stranded": max(row["stranded"] for row in games),
    }
    for key in numeric:
        output[f"average_{key}"] = statistics.fmean(row[key] for row in games)
    deployment = [row["turns_to_23_after_second_land"] for row in games if row["turns_to_23_after_second_land"] is not None]
    output["median_turns_to_23_after_second_land"] = statistics.median(deployment) if deployment else None
    return output


def _candidate_rows(games, candidates, groups):
    rows = []
    for candidate in candidates:
        selected = [row for row in games if row["candidate"] == candidate]
        group_rows = {
            group: _summary([row for row in selected if row["group"] == group])
            for group in groups
        }
        rows.append({
            "candidate": candidate,
            "path": CANDIDATES[candidate],
            "overall": _summary(selected),
            "groups": group_rows,
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("screen", "confirm"), default="screen")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--candidates", default="T0_current,T1_hands14,T2_deploy,T3_territory,T4_crop_mix,F_fertilizer")
    args = parser.parse_args()
    candidates = tuple(value for value in args.candidates.split(",") if value)
    missing = [name for name in candidates if not (ROOT / CANDIDATES[name]).exists()]
    if missing:
        raise FileNotFoundError(missing)

    if args.stage == "screen":
        seeds = (811100, 811101)
    else:
        seeds = tuple(range(812000, 812008))
    groups = {"old_synthetic": OLD_SYNTHETIC, "replay_derived": REPLAY_DERIVED}
    jobs = []
    for candidate in candidates:
        for group, opponents in groups.items():
            for opponent, path in opponents.items():
                for seed in seeds:
                    for seat in (0, 1):
                        jobs.append((candidate, CANDIDATES[candidate], group, opponent, path, seed, seat))
        for episode_id in LOSS_EPISODES:
            spec = _trace_spec(episode_id)
            replay = json.loads(Path(spec.split(":", 2)[1]).read_text())
            seed = int(replay["info"]["seed"])
            for seat in (0, 1):
                jobs.append((
                    candidate, CANDIDATES[candidate], "real_loss_reconstructed",
                    f"episode_{episode_id}", spec, seed, seat,
                ))

    games = []
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(_run, job) for job in jobs]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 40 == 0 or index == len(jobs):
                print(f"{args.stage}: {index}/{len(jobs)}", flush=True)
    group_names = (*groups, "real_loss_reconstructed")
    payload = {
        "schema_version": 1,
        "stage": args.stage,
        "seeds": list(seeds),
        "both_seats": True,
        "candidate_names": list(candidates),
        "groups": {**groups, "real_loss_reconstructed": list(LOSS_EPISODES)},
        "candidates": _candidate_rows(games, candidates, group_names),
        "games": games,
    }
    output = ROOT / "experiments" / f"post_opening_{args.stage}.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(output)
    for row in payload["candidates"]:
        overall = row["overall"]
        print(
            row["candidate"],
            f"{overall['wins']}/{overall['losses']}/{overall['ties']}",
            f"score={overall['score_rate']:.1%}",
            f"money={overall['average_money']:.0f}",
            f"adv={overall['average_advantage']:+.0f}",
            f"rev10-20={overall['average_day10_20_revenue']:.0f}",
            f"tiles={overall['average_average_productive_tiles_day10_20']:.1f}",
            f"critical={overall['average_critical_watering_miss_rate_day10_20']:.2%}",
        )


if __name__ == "__main__":
    main()
