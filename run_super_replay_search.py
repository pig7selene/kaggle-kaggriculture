"""Checkpointed staged search for elite replay and coherent phase routes."""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
from runpy import run_path
import statistics

from kaggle_environments import make

from run_epic_experiments import _independent_shop_schedule, _recorded_shop_schedule, _run_with_fixed_shops
from run_post_opening_validation import _load_opponent
from run_v27_replay_backbone import _farm_counts, _inventory_value, _semantic_validate, _transition_metrics


ROOT = Path(__file__).resolve().parent
BANK = ROOT / "experiments/super_replay_route_bank.json"
INDEX = ROOT / "agents/super_replay/index.json"
OUTPUT = ROOT / "experiments/super_replay_generation_results.json"
PARTIAL = ROOT / "experiments/super_replay_generation_results.json.partial"
K3 = "agents/v27_replay_weed_guard.py"
FROZEN = {
    "K3": K3,
    "803": "agents/opening_public_front_cow8_day6.py",
    "R3": "agents/leaderboard_r3_cow6_capital.py",
    "lifecycle": "agents/lifecycle_lc_combined.py",
}
UNIT_OPS = {"NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "PICKUP", "DROP", "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER"}
MARKET_OPS = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}


def _trace(path, player):
    return f"trace:{ROOT / path}:{int(player)}"


def _percentile(values, fraction):
    values = sorted(values)
    if not values:
        return None
    point = fraction * (len(values) - 1)
    lower = int(point)
    weight = point - lower
    return values[lower] * (1 - weight) + values[min(lower + 1, len(values) - 1)] * weight


def _run(job):
    key, candidate_path, group, opponent, opponent_spec, seed, seat, schedule, config = job
    candidate = run_path(str(ROOT / candidate_path))["agent"]
    rival = _load_opponent(opponent_spec)
    calls = 0
    semantic = []
    def checked(obs):
        nonlocal calls
        action = candidate(obs)
        try:
            _semantic_validate(obs, action)
        except Exception as error:
            semantic.append({"step": int(obs["step"]), "error": repr(error), "action": action})
        calls += 1
        return action
    pair = [rival, rival]
    pair[seat] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed), **config}, debug=True)
    runtime = None
    try:
        if schedule is None:
            env.run(pair)
        else:
            _run_with_fixed_shops(env, pair, schedule)
    except Exception as error:
        runtime = repr(error)
    if runtime or len(env.steps) != 720:
        return {"key": key, "candidate": candidate_path, "group": group, "opponent": opponent, "seed": seed, "seat": seat, "runtime_error": runtime or f"steps={len(env.steps)}", "semantic_failures": semantic}
    final = env.steps[-1]
    stranded_value, stranded = _inventory_value(final[seat])
    crops, animals, weeds = _farm_counts(final[seat].observation["farms"][seat])
    transition = _transition_metrics(env.toJSON(), seat)
    bought = Counter(transition["animal_buy_requests"])
    losses = {animal: max(0, bought[animal] - animals[animal]) for animal in ("GOOSE", "COW", "SHEEP")}
    telemetry = deepcopy(candidate.telemetry)
    return {
        "key": key, "candidate": candidate_path, "group": group, "opponent": opponent,
        "seed": int(seed), "seat": int(seat), "shop_mode": "fixed" if schedule is not None else "natural",
        "money": float(final[seat].reward), "opponent_money": float(final[1 - seat].reward),
        "advantage": float(final[seat].reward) - float(final[1 - seat].reward),
        "calls": calls, "runtime_error": None, "semantic_failures": semantic,
        "stranded_value": stranded_value, "stranded": stranded, "livestock_losses": losses,
        "final_crops": dict(crops), "final_animals": dict(animals), "final_weeds": weeds,
        "route_matches": telemetry["all_route_matches"], "route_requests": telemetry["all_route_requests"],
        "weed_repairs": telemetry["repairs"]["weed"], "repair_abort": telemetry["repair_abort"],
        "fallback_step": telemetry.get("fallback_step"), "transition": transition,
    }


def _summaries(games):
    output = {}
    for candidate in sorted({row["candidate"] for row in games}):
        rows = [row for row in games if row["candidate"] == candidate and not row.get("runtime_error")]
        advantages = [row["advantage"] for row in rows]
        total = sum(row["route_requests"] for row in rows)
        output[candidate] = {
            "games": len(rows), "wins": sum(value > 0 for value in advantages),
            "losses": sum(value < 0 for value in advantages), "ties": sum(value == 0 for value in advantages),
            "average_money": statistics.fmean(row["money"] for row in rows) if rows else None,
            "average_advantage": statistics.fmean(advantages) if rows else None,
            "median_advantage": statistics.median(advantages) if rows else None,
            "p25": _percentile(advantages, .25), "p10": _percentile(advantages, .10),
            "p5": _percentile(advantages, .05), "worst": min(advantages) if advantages else None,
            "variance": statistics.pvariance(advantages) if len(advantages) > 1 else 0,
            "route_fidelity": sum(row["route_matches"] for row in rows) / max(1, total),
            "runtime_failures": sum(bool(row.get("runtime_error")) for row in games if row["candidate"] == candidate),
            "semantic_failures": sum(len(row.get("semantic_failures", [])) for row in games if row["candidate"] == candidate),
            "livestock_losses": sum(sum(row["livestock_losses"].values()) for row in rows),
            "meaningful_stranding_games": sum(row["stranded_value"] > 500 for row in rows),
            "fallback_games": sum(row["fallback_step"] is not None for row in rows),
            "weed_repairs": sum(row["weed_repairs"] for row in rows),
            "by_group": {}, "by_opponent": {},
        }
        for group in sorted({row["group"] for row in rows}):
            subset = [row for row in rows if row["group"] == group]
            values = [row["advantage"] for row in subset]
            output[candidate]["by_group"][group] = {"games": len(subset), "wins": sum(value > 0 for value in values), "average_money": statistics.fmean(row["money"] for row in subset), "average_advantage": statistics.fmean(values), "p10": _percentile(values, .10)}
        for opponent in sorted({row["opponent"] for row in rows}):
            subset = [row for row in rows if row["opponent"] == opponent]
            values = [row["advantage"] for row in subset]
            output[candidate]["by_opponent"][opponent] = {"games": len(subset), "wins": sum(value > 0 for value in values), "average_money": statistics.fmean(row["money"] for row in subset), "average_advantage": statistics.fmean(values), "p10": _percentile(values, .10)}
    return output


def _raw_jobs(candidates):
    jobs = []
    # Cheap but adversarial Generation-0 gate: paired K3, cross-family medoids,
    # frozen architectures, and two public routes reserved from candidate data.
    bank = json.loads(BANK.read_text())
    medoids = {row["family_id"]: row for row in bank["routes"] if row["route_id"].endswith("_medoid")}
    traces = {}
    for name, route in medoids.items():
        traces[name] = (route["source_replay_path"], route["source_player"], route["source_seed"])
    reserved = [row for row in bank["routes"] if row.get("selection_tags") and row["source_submission_id"] not in {value["source_submission_id"] for value in medoids.values()}][-2:]
    for row in reserved:
        traces[f"reserved_{row['source_submission_id']}"] = (row["source_replay_path"], row["source_player"], row["source_seed"])
    for route_id, path in candidates.items():
        for seed in (994100, 994101):
            for seat in (0, 1):
                jobs.append((f"{route_id}|K3|{seed}|{seat}", path, "paired_k3", "K3", K3, seed, seat, _independent_shop_schedule(seed), {}))
                jobs.append((f"{route_id}|K3n|{seed}|{seat}", path, "natural_k3", "K3", K3, seed, seat, None, {}))
        for opponent, spec in (("803", FROZEN["803"]), ("R3", FROZEN["R3"]), ("lifecycle", FROZEN["lifecycle"])):
            for seat in (0, 1):
                seed = 994200 + len(jobs) % 7
                jobs.append((f"{route_id}|{opponent}|{seed}|{seat}", path, "frozen", opponent, spec, seed, seat, _independent_shop_schedule(seed), {}))
        for opponent, (replay_path, player, seed) in traces.items():
            replay = json.loads((ROOT / replay_path).read_text())
            for seat in (0, 1):
                jobs.append((f"{route_id}|{opponent}|{seed}|{seat}", path, "elite_trace", opponent, _trace(replay_path, player), seed, seat, _recorded_shop_schedule(replay), {}))
    return jobs


def _screen_jobs(candidates):
    jobs = []
    for route_id, path in candidates.items():
        # Eight cheap games: fixed/natural direct K3, both seats. This is only
        # an elimination screen; survivors receive the full gate separately.
        for seed in (995100, 995101):
            for seat in (0, 1):
                jobs.append((f"screen|{route_id}|f|{seed}|{seat}", path, "screen_fixed_k3", "K3", K3, seed, seat, _independent_shop_schedule(seed), {}))
                jobs.append((f"screen|{route_id}|n|{seed}|{seat}", path, "screen_natural_k3", "K3", K3, seed, seat, None, {}))
    return jobs


def _run_jobs(jobs, workers):
    if PARTIAL.is_file():
        payload = json.loads(PARTIAL.read_text())
        games = payload.get("games", [])
    else:
        games = []
    done = {row["key"] for row in games}
    todo = [job for job in jobs if job[0] not in done]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_run, job) for job in todo]
        for index, future in enumerate(as_completed(futures), 1):
            games.append(future.result())
            if index % 20 == 0 or index == len(futures):
                PARTIAL.write_text(json.dumps({"schema_version": 1, "games": games}) + "\n")
                print(f"games {index}/{len(futures)} (total {len(games)})", flush=True)
    return games


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit-candidates", type=int, default=0)
    parser.add_argument("--candidate-prefix", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--partial", default="")
    parser.add_argument("--screen", action="store_true")
    args = parser.parse_args()
    index = json.loads(INDEX.read_text())
    candidates = {"K3_baseline": K3, **index}
    if args.candidate_prefix:
        candidates = {key: value for key, value in candidates.items() if key == "K3_baseline" or key.startswith(args.candidate_prefix)}
    if args.limit_candidates:
        candidates = dict(list(candidates.items())[:args.limit_candidates])
    jobs = _screen_jobs(candidates) if args.screen else _raw_jobs(candidates)
    global PARTIAL
    if args.partial:
        PARTIAL = Path(args.partial).resolve()
    games = _run_jobs(jobs, args.workers)
    payload = {
        "schema_version": 1,
        "design": "Generation 0 raw elite routes + frozen K3 weed repair; paired fixed and independent natural RNG; both seats; cross-family route traces",
        "jobs_expected": len(jobs), "games": games, "summary": _summaries(games),
    }
    output_path = Path(args.output).resolve() if args.output else OUTPUT
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output_path)
    for path, row in sorted(payload["summary"].items(), key=lambda value: value[1]["average_advantage"], reverse=True):
        print(path, row["games"], row["wins"], round(row["average_money"], 1), round(row["average_advantage"], 1), round(row["p10"], 1), round(row["route_fidelity"], 5))


if __name__ == "__main__":
    main()
