"""Differential packaging validation for the frozen V27 K3 agent.

This is deliberately an equivalence harness, not a strategy benchmark.  Every
condition is run twice from a fresh process-local agent instance: once with the
frozen source and once with the standalone package.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from pathlib import Path
from runpy import run_path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as game

from run_epic_experiments import _recorded_shop_schedule, _run_with_fixed_shops
from run_post_opening_validation import _load_opponent


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "agents/v27_replay_weed_guard.py"
SUBMISSION = ROOT / "submission/main.py"
OUTPUT = ROOT / "experiments/v27_submission_packaging.json"
EXPECTED_SOURCE_SHA = "dc0100ec0d029a6362f92618429b09d7baba5b8a5257f20a61385fe82afeda51"
ROUTE_ID = "v27_family_3_victor_at_tufa_labs"
CHECKPOINT_STEPS = {4 * 24, 6 * 24, 8 * 24, 10 * 24, 11 * 24, 15 * 24, 20 * 24, 25 * 24, 29 * 24, 718}
PRODUCTS = tuple(game.PRODUCTS)
ANIMALS = tuple(game.ANIMALS)
UNIT_OPS = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER",
    "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE",
    "PICKUP", "DROP", "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER",
}
MARKET_OPS = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _imports(path):
    tree = ast.parse(path.read_text())
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.append(node.module or "")
    return sorted(set(found))


def _trace(path, player):
    return f"trace:{ROOT / path}:{int(player)}"


def _farm_counts(farm):
    crops, animals = Counter(), Counter()
    weeds = 0
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crops[tile.get("crop")] += 1
            elif tile.get("kind") == "WEED":
                weeds += 1
            elif tile.get("animal"):
                animals[tile["animal"]] += 1
    return dict(sorted(crops.items())), dict(sorted(animals.items())), weeds


def _summary(obs):
    me = obs["farms"][obs["player"]]
    crops, animals, weeds = _farm_counts(me)
    return {
        "step": int(obs["step"]), "day": int(obs["day"]), "hour": int(obs["hour"]),
        "money": float(me["money"]), "farmer": list(me["farmer"]),
        "hands": [list(value) for value in me["hands"]],
        "hand_count": len(me["hands"]), "quadrants": list(me["unlocked_quadrants"]),
        "crops": crops, "animals": animals, "weeds": weeds,
        "shed": dict(sorted(obs["private"]["shed"].items())),
        "seeds": dict(sorted(obs["private"]["seeds"].items())),
        "market_inventory": dict(sorted(obs["market"]["inventory"].items())),
        "market_prices": dict(sorted(obs["market"]["prices"].items())),
        "shops": list(obs["town"]["unlocked_shops"]),
    }


def _semantic_validate(obs, action):
    assert isinstance(action, dict) and set(action) == {"farmer", "hands", "market"}
    assert isinstance(action["farmer"], list) and action["farmer"] and action["farmer"][0] in UNIT_OPS
    assert isinstance(action["hands"], list)
    assert len(action["hands"]) == len(obs["farms"][obs["player"]]["hands"])
    for request in action["hands"]:
        assert isinstance(request, list) and request and request[0] in UNIT_OPS
    assert isinstance(action["market"], list) and len(action["market"]) <= 10
    for order in action["market"]:
        assert isinstance(order, list) and order and order[0] in MARKET_OPS
        if order[0] in {"HIRE", "BUY_LAND"}:
            assert len(order) == 1
        else:
            assert len(order) == 3 and isinstance(order[2], int) and order[2] > 0


def _telemetry(agent):
    raw = agent.telemetry
    return {
        "mode_steps": deepcopy(raw["mode_steps"]),
        "route": [raw["all_route_matches"], raw["all_route_requests"]],
        "farmer_route": [raw["farmer_route_matches"], raw["farmer_route_requests"]],
        "hand_route": [raw["hand_route_matches"], raw["hand_route_requests"]],
        "market_route": [raw["market_route_matches"], raw["market_route_requests"]],
        "worker_rematches": raw["worker_rematches"],
        "position_error": [raw["position_error_sum"], raw["position_error_observations"]],
        "repairs": deepcopy(raw["repairs"]),
        "repair_durations": list(raw["repair_durations"]),
        "repair_success": raw["repair_success"],
        "repair_abort": raw["repair_abort"],
        "anchor_last": deepcopy(raw["anchor_error"][-1]) if raw["anchor_error"] else None,
        "fallback_step": raw["fallback_step"],
        "fallback_reason": raw["fallback_reason"],
    }


def _inject(obs, route, pending, events):
    """Place a controlled blocking weed at the next eligible route operation."""
    if not pending:
        return
    step = int(obs["step"])
    me = obs["farms"][obs["player"]]
    positions = [me["farmer"], *me["hands"]]
    route_action = route["consensus_actions"][min(step, 718)]
    fields = [route_action["farmer"], *route_action["hands"]]
    for spec in list(pending):
        if step < spec["min_step"]:
            continue
        indices = range(min(len(positions), len(fields))) if spec["unit"] is None else (spec["unit"],)
        for unit_index in indices:
            if unit_index >= len(positions) or unit_index >= len(fields):
                continue
            planned = fields[unit_index]
            if not planned or planned[0] not in {"PLANT", "BUILD_COOP", "BUILD_PASTURE"}:
                continue
            x, y = positions[unit_index]
            if me["tiles"][y][x] is not None:
                continue
            me["tiles"][y][x] = {"kind": "WEED"}
            events.append({
                "label": spec["label"], "step": step, "unit": unit_index,
                "position": [x, y], "blocked_action": deepcopy(planned),
            })
            pending.remove(spec)
            break


def _inventory_value(final_state):
    obs = final_state.observation
    private = obs["private"]
    prices = obs["market"]["prices"]
    quantity = Counter({item: int(private["shed"].get(item, 0)) for item in PRODUCTS})
    for inventory in private["inventories"]:
        for item in PRODUCTS:
            quantity[item] += int(inventory.get(item, 0))
    value = sum(quantity[item] * prices[item] for item in PRODUCTS)
    return value, {item: quantity[item] for item in PRODUCTS if quantity[item]}


def _animal_audit(env, seat):
    escapes = []
    for index in range(1, len(env.steps)):
        before = env.steps[index - 1][seat].observation["farms"][seat]["tiles"]
        after = env.steps[index][seat].observation["farms"][seat]["tiles"]
        for y in range(len(before)):
            for x in range(len(before[y])):
                old, new = before[y][x], after[y][x]
                old_animal = old.get("animal") if isinstance(old, dict) else None
                new_animal = new.get("animal") if isinstance(new, dict) else None
                if old_animal and not new_animal and isinstance(new, dict) and new.get("kind") in {"COOP", "PASTURE"}:
                    escapes.append({"step": index - 1, "position": [x, y], "animal": old_animal})
    final_farm = env.steps[-1][seat].observation["farms"][seat]
    _, final_animals, _ = _farm_counts(final_farm)
    return escapes, final_animals


def _run_one(kind, condition):
    path = SOURCE if kind == "source" else SUBMISSION
    started = time.perf_counter_ns()
    agent = run_path(str(path))["agent"]
    import_ms = (time.perf_counter_ns() - started) / 1_000_000
    rival = _load_opponent(condition["opponent_spec"])
    calls, actions, obs_digests, states, telemetry_trace, latencies = 0, [], [], {}, [], []
    semantic_failures, exceptions, injected = [], [], []
    pending = deepcopy(condition.get("injections", []))

    def checked(obs):
        nonlocal calls
        try:
            _inject(obs, agent.route, pending, injected)
            summary = _summary(obs)
            obs_digests.append(_digest(obs))
            if int(obs["step"]) in CHECKPOINT_STEPS:
                expected = agent.route["expected_state"][min(int(obs["step"]), 718)]
                states[str(obs["step"])] = {
                    "actual": summary,
                    "expected_farmer": deepcopy(expected.get("farmer")),
                    "expected_hands": deepcopy(expected.get("hands", [])),
                }
            before = time.perf_counter_ns()
            action = agent(obs)
            latencies.append((time.perf_counter_ns() - before) / 1_000_000)
            try:
                _semantic_validate(obs, action)
            except Exception as error:
                semantic_failures.append({"step": int(obs["step"]), "error": repr(error), "action": action})
            actions.append(deepcopy(action))
            telemetry_trace.append(_telemetry(agent))
            calls += 1
            return action
        except Exception as error:
            exceptions.append({"step": int(obs.get("step", -1)), "error": repr(error)})
            raise

    pair = [rival, rival]
    pair[condition["seat"]] = checked
    configuration = {"episodeSteps": 720, "seed": int(condition["seed"]), **condition.get("config", {})}
    env = make("kaggriculture", configuration=configuration, debug=True)
    runtime_error = None
    try:
        if condition.get("schedule") is None:
            env.run(pair)
        else:
            _run_with_fixed_shops(env, pair, condition["schedule"])
    except Exception as error:
        runtime_error = repr(error)
    if runtime_error or len(env.steps) != 720:
        return {
            "kind": kind, "calls": calls, "runtime_error": runtime_error or f"steps={len(env.steps)}",
            "exceptions": exceptions, "semantic_failures": semantic_failures,
        }
    seat = condition["seat"]
    final = env.steps[-1]
    escapes, final_animals = _animal_audit(env, seat)
    stranded_value, stranded = _inventory_value(final[seat])
    telemetry_final = _telemetry(agent)
    divergent_steps = []
    previous_matches = previous_requests = 0
    for step, snapshot in enumerate(telemetry_trace):
        matches, requests = snapshot["route"]
        if matches - previous_matches < requests - previous_requests:
            divergent_steps.append(step)
        previous_matches, previous_requests = matches, requests
    return {
        "kind": kind, "calls": calls, "runtime_error": None, "exceptions": exceptions,
        "semantic_failures": semantic_failures, "actions": actions, "action_hash": _digest(actions),
        "obs_digests": obs_digests, "trajectory_hash": _digest(obs_digests), "states": states,
        "telemetry_trace": telemetry_trace, "telemetry_hash": _digest(telemetry_trace),
        "telemetry_final": telemetry_final, "route_divergent_steps": divergent_steps,
        "route_divergence_cause": "bounded weed transaction repair" if divergent_steps else None,
        "injected": injected, "untriggered_injections": pending,
        "money": float(final[seat].reward), "opponent_money": float(final[1 - seat].reward),
        "statuses": [value.status for value in final], "episode_steps": len(env.steps),
        "livestock_escapes": escapes, "final_animals": final_animals,
        "stranded_value": stranded_value, "stranded": stranded,
        "import_ms": import_ms, "first_call_ms": latencies[0],
        "average_call_ms": statistics.fmean(latencies),
        "median_call_ms": statistics.median(latencies), "max_call_ms": max(latencies),
    }


def _first_difference(left, right):
    for step, (a, b) in enumerate(zip(left.get("actions", []), right.get("actions", []))):
        if a != b:
            return {
                "kind": "action", "step": step,
                "source_action": a, "submission_action": b,
                "source_state": left.get("states", {}).get(str(step)),
                "submission_state": right.get("states", {}).get(str(step)),
                "source_telemetry": left.get("telemetry_trace", [])[step],
                "submission_telemetry": right.get("telemetry_trace", [])[step],
                "likely_cause": "standalone transformation or prior trajectory divergence",
            }
    for step, (a, b) in enumerate(zip(left.get("obs_digests", []), right.get("obs_digests", []))):
        if a != b:
            return {"kind": "trajectory", "step": step, "likely_cause": "environment trajectory diverged before action"}
    if left.get("telemetry_hash") != right.get("telemetry_hash"):
        return {"kind": "telemetry", "step": None, "likely_cause": "internal repair/rematching telemetry diverged"}
    return None


def _compact(run):
    return {key: run.get(key) for key in (
        "calls", "runtime_error", "exceptions", "semantic_failures", "action_hash", "trajectory_hash",
        "telemetry_hash", "telemetry_final", "injected", "untriggered_injections", "money",
        "route_divergent_steps", "route_divergence_cause",
        "opponent_money", "statuses", "episode_steps", "livestock_escapes", "final_animals",
        "stranded_value", "stranded", "import_ms", "first_call_ms", "average_call_ms",
        "median_call_ms", "max_call_ms",
    )}


def _run_pair(condition):
    source = _run_one("source", condition)
    submission = _run_one("submission", condition)
    first = _first_difference(source, submission)
    equivalent = (
        first is None
        and source.get("runtime_error") is None and submission.get("runtime_error") is None
        and source.get("calls") == submission.get("calls") == 719
        and source.get("money") == submission.get("money")
        and source.get("states") == submission.get("states")
        and source.get("livestock_escapes") == submission.get("livestock_escapes")
        and source.get("stranded_value") == submission.get("stranded_value")
    )
    return {
        "name": condition["name"], "group": condition["group"], "seed": condition["seed"],
        "seat": condition["seat"], "opponent": condition["opponent"],
        "equivalent": equivalent, "first_mismatch": first,
        "source": _compact(source), "submission": _compact(submission),
    }


def _conditions():
    source_replay_path = "experiments/top_player_replays/replays/episode-91876492-replay.json"
    source_replay = json.loads((ROOT / source_replay_path).read_text())
    rows = [{
        "name": "victor_source_91876492", "group": "source_replay", "seed": int(source_replay["info"]["seed"]),
        "seat": 0, "opponent": "Jince_trace", "opponent_spec": _trace(source_replay_path, 1),
        "schedule": _recorded_shop_schedule(source_replay), "config": {},
    }]

    local = [
        ("frozen_803", "agents/opening_public_front_cow8_day6.py"),
        ("R3", "agents/leaderboard_r3_cow6_capital.py"),
        ("lifecycle", "agents/lifecycle_lc_combined.py"),
    ]
    for index, seed in enumerate(range(997300, 997308)):
        opponent, spec = local[index % len(local)]
        for seat in (0, 1):
            rows.append({
                "name": f"fresh_{seed}_s{seat}_{opponent}", "group": "fresh", "seed": seed,
                "seat": seat, "opponent": opponent, "opponent_spec": spec, "schedule": None, "config": {},
            })

    strong_replays = {
        "Filip": ("experiments/leaderboard_replays/submission_55438811/replays/episode-92075718-replay.json", 1),
        "Amer": ("experiments/leaderboard_replays/submission_55438811/replays/episode-92057764-replay.json", 1),
        "Yankang": ("experiments/leaderboard_replays/submission_55435253/replays/episode-92177850-replay.json", 0),
        "Prashant": ("experiments/leaderboard_replays/submission_55435253/replays/episode-92015550-replay.json", 1),
        "Jayveer": ("experiments/leaderboard_replays/submission_55435253/replays/episode-92008833-replay.json", 0),
        "Pedro": ("experiments/leaderboard_replays/submission_55435253/replays/episode-92010768-replay.json", 1),
        "Lucas": ("experiments/leaderboard_replays/submission_55435253/replays/episode-92009080-replay.json", 1),
        "Alexander": ("experiments/leaderboard_replays/submission_55435253/replays/episode-92011750-replay.json", 0),
    }
    for index, (opponent, spec) in enumerate(local):
        for seat in (0, 1):
            rows.append({
                "name": f"strong_{opponent}_s{seat}", "group": "strong", "seed": 997500 + index,
                "seat": seat, "opponent": opponent, "opponent_spec": spec, "schedule": None, "config": {},
            })
    for opponent, (path, player) in strong_replays.items():
        replay = json.loads((ROOT / path).read_text())
        for seat in (0, 1):
            rows.append({
                "name": f"strong_{opponent}_s{seat}", "group": "strong", "seed": int(replay["info"]["seed"]),
                "seat": seat, "opponent": opponent, "opponent_spec": _trace(path, player),
                "schedule": _recorded_shop_schedule(replay), "config": {},
            })

    weed_cases = {
        "weed_none": [],
        "weed_single_farmer": [{"label": "farmer", "min_step": 0, "unit": 0}],
        "weed_single_hand": [{"label": "hand_1", "min_step": 0, "unit": 1}],
        "weed_repeated_workers": [
            {"label": "early_hand_1", "min_step": 0, "unit": 1},
            {"label": "middle_hand_2", "min_step": 120, "unit": 2},
            {"label": "late_any_worker", "min_step": 240, "unit": None},
        ],
        "weed_critical_route": [
            {"label": "near_first_land", "min_step": 155, "unit": None},
            {"label": "near_second_land", "min_step": 235, "unit": None},
        ],
    }
    for index, (name, injections) in enumerate(weed_cases.items()):
        rows.append({
            "name": name, "group": "weed", "seed": 997700 + index, "seat": index % 2,
            "opponent": "lifecycle", "opponent_spec": "agents/lifecycle_lc_combined.py",
            "schedule": None, "config": {"weedSpawnChance": 0}, "injections": injections,
        })
    return rows


def _clean_directory_test():
    script = r'''import hashlib,json,resource,time
from pathlib import Path
from runpy import run_path
from kaggle_environments import make
p=Path("main.py")
t=time.perf_counter_ns(); a=run_path(str(p))["agent"]; import_ms=(time.perf_counter_ns()-t)/1e6
calls=0; first=None; values=[]
def checked(obs):
 global calls,first
 t=time.perf_counter_ns(); out=a(obs); elapsed=(time.perf_counter_ns()-t)/1e6
 if first is None: first=elapsed
 values.append(elapsed); calls+=1; return out
env=make("kaggriculture", configuration={"episodeSteps":720,"seed":997999}, debug=True)
env.run([checked,"starter"])
f=env.steps[-1]
print(json.dumps({"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"calls":calls,"steps":len(env.steps),"statuses":[x.status for x in f],"money":[x.reward for x in f],"import_ms":import_ms,"first_call_ms":first,"average_call_ms":sum(values)/len(values),"median_call_ms":sorted(values)[len(values)//2],"max_call_ms":max(values),"peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
'''
    with tempfile.TemporaryDirectory(prefix="v27-standalone-") as raw:
        directory = Path(raw)
        shutil.copy2(SUBMISSION, directory / "main.py")
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=directory, text=True, capture_output=True,
            timeout=180, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if result.returncode:
            return {"pass": False, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
        payload = json.loads(result.stdout.strip().splitlines()[-1])
        payload["pass"] = payload["calls"] == 719 and payload["steps"] == 720 and payload["statuses"] == ["DONE", "DONE"]
        payload["directory_contents_before_cleanup"] = sorted(value.name for value in directory.iterdir())
        return payload


def _dependency_audit():
    imports = _imports(SUBMISSION)
    text = SUBMISSION.read_text()
    forbidden_runtime_tokens = [
        token for token in ("run_path(", "open(", "Path(", "requests.", "urllib.", "socket.") if token in text
    ]
    project_imports = [value for value in imports if value.startswith(("agents", "experiments", "run_", "analyze_", "test_"))]
    embedded_route_id = run_path(str(SUBMISSION))["agent"].route.get("route_id") == ROUTE_ID
    return {
        "imports": imports,
        "project_local_imports": project_imports,
        "forbidden_runtime_tokens": forbidden_runtime_tokens,
        "embedded_route_id": embedded_route_id,
        "pass": not project_imports and not forbidden_runtime_tokens and embedded_route_id,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    source_before = _sha256(SOURCE)
    if source_before != EXPECTED_SOURCE_SHA:
        raise SystemExit(f"frozen source hash mismatch: expected {EXPECTED_SOURCE_SHA}, got {source_before}")
    conditions = _conditions()
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_run_pair, row): row for row in conditions}
        for future in as_completed(futures):
            result = future.result()
            rows.append(result)
            print(f"{result['name']}: {'PASS' if result['equivalent'] else 'FAIL'}")
    order = {row["name"]: index for index, row in enumerate(conditions)}
    rows.sort(key=lambda row: order[row["name"]])
    clean = _clean_directory_test()
    dependency = _dependency_audit()
    source_after = _sha256(SOURCE)
    package_runs = [row["submission"] for row in rows]
    route_matches = sum(row["telemetry_final"]["route"][0] for row in package_runs)
    route_requests = sum(row["telemetry_final"]["route"][1] for row in package_runs)
    source_route_matches = sum(row["source"]["telemetry_final"]["route"][0] for row in rows)
    source_route_requests = sum(row["source"]["telemetry_final"]["route"][1] for row in rows)
    result = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": str(SOURCE.relative_to(ROOT)), "submission": str(SUBMISSION.relative_to(ROOT)),
        "source_expected_sha256": EXPECTED_SOURCE_SHA, "source_sha256_before": source_before,
        "source_sha256_after": source_after, "submission_sha256": _sha256(SUBMISSION),
        "current_best_sha256": _sha256(ROOT / "experiments/current_best.json"),
        "submission_size_bytes": SUBMISSION.stat().st_size,
        "dependency_audit": dependency, "clean_directory_test": clean,
        "condition_count": len(rows), "paired_game_count": len(rows), "actual_game_count": len(rows) * 2 + 1,
        "groups": {
            group: {
                "pairs": sum(row["group"] == group for row in rows),
                "passed": sum(row["group"] == group and row["equivalent"] for row in rows),
            }
            for group in ("source_replay", "fresh", "strong", "weed")
        },
        "all_equivalent": all(row["equivalent"] for row in rows),
        "semantic_failures": sum(len(row["source"]["semantic_failures"]) + len(row["submission"]["semantic_failures"]) for row in rows),
        "runtime_failures": sum(bool(row["source"]["runtime_error"] or row["submission"]["runtime_error"]) for row in rows),
        "livestock_escapes": sum(len(row["submission"]["livestock_escapes"]) for row in rows),
        "meaningful_stranding_threshold": 500,
        "meaningful_stranding_games": sum(row["submission"]["stranded_value"] > 500 for row in rows),
        "route_fidelity": {
            "source_matches": source_route_matches, "source_requests": source_route_requests,
            "source_percent": 100 * source_route_matches / source_route_requests,
            "submission_matches": route_matches, "submission_requests": route_requests,
            "submission_percent": 100 * route_matches / route_requests,
            "delta_percentage_points": 100 * (route_matches / route_requests - source_route_matches / source_route_requests),
        },
        "performance": {
            "import_ms_median": statistics.median(row["import_ms"] for row in package_runs),
            "import_ms_max": max(row["import_ms"] for row in package_runs),
            "first_call_ms_median": statistics.median(row["first_call_ms"] for row in package_runs),
            "first_call_ms_max": max(row["first_call_ms"] for row in package_runs),
            "average_call_ms_median": statistics.median(row["average_call_ms"] for row in package_runs),
            "average_call_ms_max": max(row["average_call_ms"] for row in package_runs),
            "typical_call_ms_median": statistics.median(row["median_call_ms"] for row in package_runs),
            "maximum_observed_call_ms": max(row["max_call_ms"] for row in package_runs),
        },
        "results": rows,
    }
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: result[key] for key in ("all_equivalent", "semantic_failures", "runtime_failures", "livestock_escapes", "meaningful_stranding_games", "route_fidelity", "performance")}, indent=2))


if __name__ == "__main__":
    main()
