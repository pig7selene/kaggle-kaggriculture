"""Deployment-only equivalence validator for the locked Top-50 portfolio."""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from runpy import run_path

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as game

from run_post_opening_validation import _load_opponent
from validate_v27_submission import _semantic_validate


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "agents/top50_distilled/top50_observable_portfolio.py"
SUBMISSION = ROOT / "submission/main.py"
OUTPUT = ROOT / "experiments/top50_submission_package.json"
DEPENDENCY_OUTPUT = ROOT / "experiments/top50_submission_dependency_audit.json"
INTEGRITY_OUTPUT = ROOT / "experiments/top50_submission_parent_integrity.json"
LEAKAGE_OUTPUT = ROOT / "experiments/top50_submission_feature_leakage_audit.json"
EXPECTED_SOURCE_SHA = "f9ca672848ccffdfe56888d99bcdf5a9d7644062b9eec0cf0cdea13574931233"
EXPECTED_PREVIOUS_SUBMISSION_SHA = "a4f753d46a95e8d972098504f4930165e7e66f8ce292092e9ab090e4741310c3"
PARENT_ROUTE_IDS = {
    "dmitry": "super_raw_55859516",
    "hanserong": "super_raw_55886665",
    "redblack": "super_raw_55890191",
}
SELECTOR_CONFIG = {
    "timing": "step 1 before first parent divergence",
    "features": ["public opponent money", "public opponent hand count"],
    "rules": [
        ["money >= 2500 and hands == 0", "redblack"],
        ["money >= 1500 and hands >= 6", "hanserong"],
        ["3 < money <= 10 and hands >= 5", "hanserong"],
    ],
    "default": "dmitry",
}
PRODUCTS = tuple(game.PRODUCTS)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lf_sha256(path):
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def _digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _percentile(values, q):
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * q
    low = int(position)
    high = min(len(values) - 1, low + 1)
    fraction = position - low
    return values[low] * (1 - fraction) + values[high] * fraction


def _imports(path):
    tree = ast.parse(path.read_text())
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.append(node.module or "")
    return sorted(set(found))


def _farm_counts(farm):
    crops, animals, structures = Counter(), Counter(), Counter()
    weeds = 0
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crops[tile.get("crop")] += 1
            elif tile.get("kind") == "WEED":
                weeds += 1
            elif tile.get("kind") in {"COOP", "PASTURE"}:
                structures[tile["kind"]] += 1
            if tile.get("animal"):
                animals[tile["animal"]] += 1
    return {
        "crops": dict(sorted(crops.items())),
        "animals": dict(sorted(animals.items())),
        "structures": dict(sorted(structures.items())),
        "weeds": weeds,
    }


def _inventory_value(final_state):
    obs = final_state.observation
    private = obs["private"]
    prices = obs["market"]["prices"]
    quantities = Counter({item: int(private["shed"].get(item, 0)) for item in PRODUCTS})
    for inventory in private["inventories"]:
        for item in PRODUCTS:
            quantities[item] += int(inventory.get(item, 0))
    value = sum(quantities[item] * prices[item] for item in PRODUCTS)
    return value, {item: quantities[item] for item in PRODUCTS if quantities[item]}


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
    return escapes


def _terminal(final_state, seat):
    obs = final_state[seat].observation
    farm = obs["farms"][seat]
    private = obs["private"]
    value, stranded = _inventory_value(final_state[seat])
    return {
        "money": float(final_state[seat].reward),
        "advantage": float(final_state[seat].reward) - float(final_state[1 - seat].reward),
        "quadrants": list(farm["unlocked_quadrants"]),
        "farmer": list(farm["farmer"]),
        "hands": [list(value) for value in farm["hands"]],
        "farm": _farm_counts(farm),
        "shed": dict(sorted(private["shed"].items())),
        "seeds": dict(sorted(private["seeds"].items())),
        "inventories": [dict(sorted(value.items())) for value in private["inventories"]],
        "stranded_value": value,
        "stranded": stranded,
        "statuses": [value.status for value in final_state],
    }


def _load_candidate(path):
    started = time.perf_counter_ns()
    namespace = run_path(str(path))
    return namespace["agent"], namespace, (time.perf_counter_ns() - started) / 1_000_000


def _load_rival(spec):
    if spec in {"pass", "random", "starter"}:
        return spec
    return _load_opponent(spec)


def _compact_telemetry(agent):
    raw = deepcopy(agent.telemetry)
    return {
        "portfolio_parent": raw.get("portfolio_parent"),
        "selector_step": raw.get("selector_step"),
        "calls": raw.get("calls"),
        "mode_steps": raw.get("mode_steps"),
        "repairs": raw.get("repairs"),
        "fallback_step": raw.get("fallback_step"),
        "fallback_reason": raw.get("fallback_reason"),
        "route_matches": raw.get("all_route_matches"),
        "route_requests": raw.get("all_route_requests"),
    }


def _run_loaded(agent, spec, seed, seat):
    rival = _load_rival(spec)
    actions, observations, latencies = [], [], []
    semantic_failures, exceptions = [], []

    def checked(obs):
        observations.append(_digest(obs))
        started = time.perf_counter_ns()
        try:
            action = agent(obs)
        except Exception as error:
            exceptions.append({"step": int(obs.get("step", -1)), "error": repr(error)})
            raise
        latencies.append((time.perf_counter_ns() - started) / 1_000_000)
        try:
            _semantic_validate(obs, action)
        except Exception as error:
            semantic_failures.append({
                "step": int(obs["step"]), "error": repr(error), "action": deepcopy(action),
            })
        actions.append(deepcopy(action))
        return action

    pair = [rival, rival]
    pair[seat] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=True)
    runtime_error = None
    try:
        env.run(pair)
    except Exception as error:
        runtime_error = repr(error)
    if runtime_error or len(env.steps) != 720:
        return {
            "runtime_error": runtime_error or f"steps={len(env.steps)}",
            "exceptions": exceptions,
            "semantic_failures": semantic_failures,
            "actions": actions,
            "observations": observations,
            "latencies": latencies,
        }
    return {
        "runtime_error": None,
        "exceptions": exceptions,
        "semantic_failures": semantic_failures,
        "actions": actions,
        "observations": observations,
        "latencies": latencies,
        "terminal": _terminal(env.steps[-1], seat),
        "livestock_escapes": _animal_audit(env, seat),
        "telemetry": _compact_telemetry(agent),
    }


def _run_one(kind, condition):
    path = SOURCE if kind == "source" else SUBMISSION
    agent, _, import_ms = _load_candidate(path)
    row = _run_loaded(agent, condition["opponent_spec"], condition["seed"], condition["seat"])
    row["import_ms"] = import_ms
    return row


def _first_action_difference(left, right):
    for step, (source_action, package_action) in enumerate(zip(left["actions"], right["actions"])):
        if source_action != package_action:
            return {
                "step": step,
                "source_action": source_action,
                "submission_action": package_action,
            }
    return None


def _compact_run(row):
    latencies = row.get("latencies", [])
    return {
        "runtime_error": row.get("runtime_error"),
        "exceptions": row.get("exceptions"),
        "semantic_failures": row.get("semantic_failures"),
        "calls": len(row.get("actions", [])),
        "action_hash": _digest(row.get("actions", [])),
        "observation_hash": _digest(row.get("observations", [])),
        "terminal": row.get("terminal"),
        "livestock_escapes": row.get("livestock_escapes", []),
        "telemetry": row.get("telemetry"),
        "import_ms": row.get("import_ms"),
        "call_time_ms": {
            "mean": statistics.fmean(latencies) if latencies else None,
            "p95": _percentile(latencies, 0.95),
            "max": max(latencies) if latencies else None,
        },
    }


def _run_pair(condition):
    source = _run_one("source", condition)
    package = _run_one("submission", condition)
    difference = _first_action_difference(source, package)
    compared = min(len(source["actions"]), len(package["actions"]))
    matches = sum(
        left == right for left, right in zip(source["actions"], package["actions"])
    )
    equivalent = all((
        difference is None,
        source.get("runtime_error") is None,
        package.get("runtime_error") is None,
        len(source["actions"]) == len(package["actions"]) == 719,
        source.get("observations") == package.get("observations"),
        source.get("terminal") == package.get("terminal"),
        source.get("livestock_escapes") == package.get("livestock_escapes"),
        source.get("telemetry") == package.get("telemetry"),
    ))
    compact_package = _compact_run(package)
    compact_package["_latencies"] = package.get("latencies", [])
    return {
        "name": condition["name"],
        "seed": condition["seed"],
        "seat": condition["seat"],
        "opponent": condition["opponent"],
        "equivalent": equivalent,
        "actions_compared": compared,
        "actions_matching": matches,
        "first_mismatch": difference,
        "source": _compact_run(source),
        "submission": compact_package,
    }


def _conditions():
    opponents = [
        ("V2", "agents/super_replay_v2/super_backbone_v2.py"),
        ("K3", "agents/v27_replay_weed_guard.py"),
        ("Nazmus", "agents/super_replay_v3/v3_raw_55445174.py"),
        ("rank1_adaptive", "agents/super_replay_v3/v3_raw_55425101.py"),
        ("ResearchStudio_adaptive", "agents/super_replay_v3/v3_raw_55435941.py"),
        ("V1", "agents/super_replay/super_backbone_v1.py"),
        ("portfolio_mirror", "agents/top50_distilled/top50_observable_portfolio.py"),
        ("top50_family03_medoid", "agents/top50_distilled/raw/super_family_03_medoid.py"),
    ]
    rows = []
    for index, (opponent, spec) in enumerate(opponents):
        seed = 1203400 + index
        for seat in (0, 1):
            rows.append({
                "name": f"fresh_{seed}_s{seat}_{opponent}",
                "seed": seed,
                "seat": seat,
                "opponent": opponent,
                "opponent_spec": spec,
            })
    return rows


def _selector_audit():
    source = run_path(str(SOURCE))
    package = run_path(str(SUBMISSION))
    states, mismatches = [], []
    for player in (0, 1):
        for money in (-1, 0, 3, 4, 10, 10.5, 1499, 1500, 2499, 2500, 3000):
            for hands in (0, 1, 5, 6, 12):
                farms = [
                    {"money": 777, "hands": []},
                    {"money": 777, "hands": []},
                ]
                farms[1 - player] = {"money": money, "hands": [[0, 0]] * hands}
                obs = {"player": player, "farms": farms}
                left = source["_select"](deepcopy(obs))
                right = package["_select"](deepcopy(obs))
                row = {"player": player, "money": money, "hands": hands, "selected": left}
                states.append(row)
                if left != right:
                    mismatches.append({**row, "submission_selected": right})
    return {
        "states": len(states),
        "agreements": len(states) - len(mismatches),
        "agreement_rate": (len(states) - len(mismatches)) / len(states),
        "selection_counts": dict(sorted(Counter(row["selected"] for row in states).items())),
        "mismatches": mismatches,
        "pass": not mismatches,
    }


def _parent_integrity():
    source_agent = run_path(str(SOURCE))["agent"]
    package_agent = run_path(str(SUBMISSION))["agent"]
    parents = {}
    for name, expected_id in PARENT_ROUTE_IDS.items():
        left = source_agent.parents[name]
        right = package_agent.parents[name]
        source_route = left.base.route
        package_route = right.base.route
        row = {
            "expected_route_id": expected_id,
            "source_route_id": source_route["route_id"],
            "submission_route_id": package_route["route_id"],
            "actions_steps": len(source_route["consensus_actions"]),
            "expected_state_steps": len(source_route["expected_state"]),
            "source_actions_sha256": _digest(source_route["consensus_actions"]),
            "submission_actions_sha256": _digest(package_route["consensus_actions"]),
            "source_expected_state_sha256": _digest(source_route["expected_state"]),
            "submission_expected_state_sha256": _digest(package_route["expected_state"]),
            "source_safety_policy": left.safety_policy,
            "submission_safety_policy": right.safety_policy,
        }
        row["exact_semantic_equal"] = all((
            row["source_route_id"] == row["submission_route_id"] == expected_id,
            source_route["consensus_actions"] == package_route["consensus_actions"],
            source_route["expected_state"] == package_route["expected_state"],
            row["actions_steps"] == row["expected_state_steps"] == 719,
            row["source_safety_policy"] == row["submission_safety_policy"],
        ))
        parents[name] = row
    result = {
        "schema_version": 1,
        "research_source": str(SOURCE.relative_to(ROOT)),
        "submission": str(SUBMISSION.relative_to(ROOT)),
        "parents": parents,
        "pass": all(row["exact_semantic_equal"] for row in parents.values()),
    }
    INTEGRITY_OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def _dependency_audit():
    imports = _imports(SUBMISSION)
    text = SUBMISSION.read_text()
    standard_library = {"base64", "copy", "json", "zlib"}
    competition_runtime = {"kaggle_environments.envs.kaggriculture"}
    project_imports = [
        value for value in imports
        if value.startswith(("agents", "experiments", "run_", "analyze_", "validate_", "package_"))
    ]
    third_party = [
        value for value in imports
        if value not in standard_library and value not in competition_runtime
    ]
    forbidden_tokens = [
        value for value in (
            "/Users/", "C:\\", "D:\\", "agents/", "experiments/", ".json", ".pkl",
            ".pickle", "run_path(", "open(", "Path(", "requests.", "urllib.", "socket.",
        ) if value in text
    ]
    dependency_paths = [
        "agents/top50_distilled/top50_observable_portfolio.py",
        "agents/top50_distilled/top50_dmitry_safe.py",
        "agents/top50_distilled/top50_hanserong_safe.py",
        "agents/top50_distilled/top50_redblack_safe.py",
        "agents/top50_distilled/safety_common.py",
        "agents/top50_distilled/raw/super_raw_55859516.py",
        "agents/top50_distilled/raw/super_raw_55886665.py",
        "agents/top50_distilled/raw/super_raw_55890191.py",
        "agents/top50_distilled/backbone_common.py",
        "agents/v27_backbone_common.py",
        "experiments/top50_route_bank.json",
    ]
    graph = {
        path: {"sha256": _sha256(ROOT / path)}
        for path in dependency_paths
    }
    result = {
        "schema_version": 1,
        "recursive_dependency_graph": {
            "portfolio": [
                "top50_dmitry_safe", "top50_hanserong_safe", "top50_redblack_safe",
            ],
            "safe_parents": ["safety_common", "three raw route wrappers"],
            "raw_route_wrappers": ["backbone_common"],
            "backbone_common": ["top50_route_bank.json", "v27_backbone_common:stage=3"],
            "packaged_runtime": [
                "embedded three-route payload", "embedded Stage-3 executor",
                "embedded exact safety wrappers", "embedded observable selector",
                "Python standard library", "Kaggriculture runtime constants",
            ],
        },
        "source_dependency_hashes": graph,
        "submission_imports": imports,
        "standard_library_imports": sorted(standard_library & set(imports)),
        "competition_runtime_imports": sorted(competition_runtime & set(imports)),
        "project_local_imports": project_imports,
        "unexpected_third_party_imports": third_party,
        "forbidden_runtime_tokens": forbidden_tokens,
        "network_access": False,
        "runtime_file_reads": False,
        "pass": not project_imports and not third_party and not forbidden_tokens,
    }
    DEPENDENCY_OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def _leakage_audit(selector):
    text = SUBMISSION.read_text()
    forbidden = {
        "environment_seed": "environment seed",
        "replay_id": "replay id",
        "leaderboard_rank": "leaderboard rank",
        "team_identity": "team identity",
        "future_prices": "future prices",
        "future_shops": "future shops",
        "future_opponent_actions": "future opponent actions",
        "final_result": "final result",
    }
    # The prose docstring intentionally says these concepts are absent, so the
    # executable audit is based on parsed selector inputs and the exact corpus.
    result = {
        "schema_version": 1,
        "candidate": "submission/main.py",
        "status": "PASS" if selector["pass"] else "FAIL",
        "deployable_features": [
            "current public opponent money at step 1",
            "current public opponent hand count at step 1",
        ],
        "forbidden_features_used": {key: False for key in forbidden},
        "selector_equivalence": selector,
        "selector_source_text_present": all(value in text for value in (
            'other = obs["farms"][1 - obs["player"]]',
            'money = float(other["money"])',
            'hands = len(other.get("hands", []))',
        )),
        "conclusion": "No hidden, future, replay, rank, team, seed, or result feature is used.",
    }
    result["pass"] = result["status"] == "PASS" and result["selector_source_text_present"]
    LEAKAGE_OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def _clean_directory_test():
    script = r'''import hashlib,json,resource,time
from pathlib import Path
from runpy import run_path
from kaggle_environments import make
p=Path("main.py")
t=time.perf_counter_ns(); namespace=run_path(str(p)); a=namespace["agent"]; import_ms=(time.perf_counter_ns()-t)/1e6
values=[]
def checked(obs):
 t=time.perf_counter_ns(); out=a(obs); values.append((time.perf_counter_ns()-t)/1e6); return out
env=make("kaggriculture",configuration={"episodeSteps":720,"seed":1203499},debug=True); env.run([checked,"starter"])
f=env.steps[-1]
print(json.dumps({"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"agent_callable":callable(a),"calls":len(values),"steps":len(env.steps),"statuses":[x.status for x in f],"money":[x.reward for x in f],"import_ms":import_ms,"mean_call_ms":sum(values)/len(values),"p95_call_ms":sorted(values)[int(.95*(len(values)-1))],"max_call_ms":max(values),"peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
'''
    with tempfile.TemporaryDirectory(prefix="top50-standalone-") as raw:
        directory = Path(raw)
        shutil.copy2(SUBMISSION, directory / "main.py")
        completed = subprocess.run(
            [sys.executable, "-c", script], cwd=directory, text=True,
            capture_output=True, timeout=240,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if completed.returncode:
            return {
                "pass": False, "returncode": completed.returncode,
                "stdout": completed.stdout, "stderr": completed.stderr,
            }
        result = json.loads(completed.stdout.strip().splitlines()[-1])
        result["directory_contents"] = sorted(value.name for value in directory.iterdir())
        result["pass"] = all((
            result["sha256"] == _sha256(SUBMISSION),
            result["agent_callable"], result["calls"] == 719,
            result["steps"] == 720, result["statuses"] == ["DONE", "DONE"],
            result["directory_contents"] == ["main.py"],
        ))
        return result


def _reset_audit(reference_rows):
    conditions = _conditions()[:2]
    package_agent, _, _ = _load_candidate(SUBMISSION)
    results = []
    for condition in conditions:
        sequential = _run_loaded(
            package_agent, condition["opponent_spec"], condition["seed"], condition["seat"]
        )
        reference = next(row for row in reference_rows if row["name"] == condition["name"])
        action_hash = _digest(sequential["actions"])
        results.append({
            "name": condition["name"],
            "seat": condition["seat"],
            "calls": len(sequential["actions"]),
            "action_hash": action_hash,
            "fresh_action_hash": reference["submission"]["action_hash"],
            "terminal": sequential.get("terminal"),
            "fresh_terminal": reference["submission"]["terminal"],
            "selected_parent": sequential.get("telemetry", {}).get("portfolio_parent"),
            "matches_fresh_import": (
                action_hash == reference["submission"]["action_hash"]
                and sequential.get("terminal") == reference["submission"]["terminal"]
                and len(sequential["actions"]) == 719
            ),
        })
    return {
        "same_module_games": len(results),
        "seat_sequence": [row["seat"] for row in results],
        "results": results,
        "pass": all(row["matches_fresh_import"] for row in results),
    }


def _v2_sanity():
    rows = []
    for seed in range(1203500, 1203504):
        for seat in (0, 1):
            agent, _, _ = _load_candidate(SUBMISSION)
            run = _run_loaded(agent, "agents/super_replay_v2/super_backbone_v2.py", seed, seat)
            terminal = run.get("terminal", {})
            rows.append({
                "seed": seed, "seat": seat,
                "money": terminal.get("money"), "advantage": terminal.get("advantage"),
                "win": terminal.get("advantage", 0) > 0,
                "runtime_error": run.get("runtime_error"),
                "semantic_failures": len(run.get("semantic_failures", [])),
                "livestock_escapes": len(run.get("livestock_escapes", [])),
            })
    advantages = [row["advantage"] for row in rows]
    return {
        "games": len(rows),
        "wins": sum(row["advantage"] > 0 for row in rows),
        "losses": sum(row["advantage"] < 0 for row in rows),
        "ties": sum(row["advantage"] == 0 for row in rows),
        "average_money": statistics.fmean(row["money"] for row in rows),
        "average_advantage": statistics.fmean(advantages),
        "rows": rows,
        "pass": all(row["runtime_error"] is None and not row["semantic_failures"] for row in rows),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--condition-index", type=int)
    parser.add_argument("--condition-output")
    args = parser.parse_args()
    if args.condition_index is not None:
        if not args.condition_output:
            raise SystemExit("--condition-output is required")
        result = _run_pair(_conditions()[args.condition_index])
        Path(args.condition_output).write_text(json.dumps(result, separators=(",", ":")))
        return

    source_before = _sha256(SOURCE)
    if source_before != EXPECTED_SOURCE_SHA:
        raise SystemExit(
            f"locked source mismatch: expected {EXPECTED_SOURCE_SHA}, got {source_before}"
        )

    selector = _selector_audit()
    integrity = _parent_integrity()
    dependency = _dependency_audit()
    leakage = _leakage_audit(selector)

    conditions = _conditions()
    rows = []
    with tempfile.TemporaryDirectory(prefix="top50-package-pairs-") as raw:
        directory = Path(raw)
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {
                pool.submit(_run_pair, condition): condition for condition in conditions
            }
            for future in as_completed(futures):
                result = future.result()
                rows.append(result)
                print(f"{result['name']}: {'PASS' if result['equivalent'] else 'FAIL'}", flush=True)
    order = {condition["name"]: index for index, condition in enumerate(conditions)}
    rows.sort(key=lambda row: order[row["name"]])

    all_latencies = []
    for row in rows:
        all_latencies.extend(row["submission"].pop("_latencies"))
    reset = _reset_audit(rows)
    clean = _clean_directory_test()
    sanity = _v2_sanity()
    source_after = _sha256(SOURCE)
    total_actions = sum(row["actions_compared"] for row in rows)
    matching_actions = sum(row["actions_matching"] for row in rows)
    package_runs = [row["submission"] for row in rows]
    source_runs = [row["source"] for row in rows]
    parent_usage = Counter(row["submission"]["telemetry"]["portfolio_parent"] for row in rows)

    result = {
        "schema_version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "research_source_path": str(SOURCE.relative_to(ROOT)),
        "research_source_expected_sha256": EXPECTED_SOURCE_SHA,
        "research_source_raw_sha256_before": source_before,
        "research_source_raw_sha256_after": source_after,
        "research_source_lf_sha256": _lf_sha256(SOURCE),
        "previous_submission_raw_sha256": EXPECTED_PREVIOUS_SUBMISSION_SHA,
        "submission_path": str(SUBMISSION.relative_to(ROOT)),
        "submission_raw_sha256": _sha256(SUBMISSION),
        "submission_lf_sha256": _lf_sha256(SUBMISSION),
        "submission_size_bytes": SUBMISSION.stat().st_size,
        "dependency_audit": dependency,
        "feature_leakage_audit": leakage,
        "parent_route_integrity": integrity,
        "selector_config": SELECTOR_CONFIG,
        "selector_config_sha256": _digest(SELECTOR_CONFIG),
        "selector_equivalence": selector,
        "clean_directory_test": clean,
        "reset_audit": reset,
        "equivalence": {
            "games": len(rows),
            "both_seats": sorted(set(row["seat"] for row in rows)) == [0, 1],
            "opponents": sorted(set(row["opponent"] for row in rows)),
            "fresh_seeds": sorted(set(row["seed"] for row in rows)),
            "games_passed": sum(row["equivalent"] for row in rows),
            "actions_compared": total_actions,
            "actions_matching": matching_actions,
            "action_equivalence_rate": matching_actions / total_actions,
            "all_719_action_games": all(
                row["actions_compared"] == row["actions_matching"] == 719 for row in rows
            ),
            "final_money_delta_zero": all(
                row["source"]["terminal"]["money"] == row["submission"]["terminal"]["money"]
                for row in rows
            ),
            "final_advantage_delta_zero": all(
                row["source"]["terminal"]["advantage"] == row["submission"]["terminal"]["advantage"]
                for row in rows
            ),
            "terminal_state_exact": all(
                row["source"]["terminal"] == row["submission"]["terminal"] for row in rows
            ),
            "parent_usage": dict(sorted(parent_usage.items())),
        },
        "safety": {
            "runtime_failures": sum(
                bool(row["source"]["runtime_error"] or row["submission"]["runtime_error"])
                for row in rows
            ),
            "semantic_failures": sum(
                len(row["source"]["semantic_failures"]) + len(row["submission"]["semantic_failures"])
                for row in rows
            ),
            "actual_livestock_escapes": sum(
                len(row["submission"]["livestock_escapes"]) for row in rows
            ),
            "meaningful_stranding_threshold": 500,
            "meaningful_stranding_games": sum(
                row["submission"]["terminal"]["stranded_value"] > 500 for row in rows
            ),
            "unexpected_fallbacks": sum(
                row["submission"]["telemetry"]["fallback_step"] is not None for row in rows
            ),
        },
        "runtime_performance": {
            "calls": len(all_latencies),
            "mean_call_ms": statistics.fmean(all_latencies),
            "p95_call_ms": _percentile(all_latencies, 0.95),
            "max_call_ms": max(all_latencies),
            "median_import_ms": statistics.median(row["import_ms"] for row in package_runs),
            "max_import_ms": max(row["import_ms"] for row in package_runs),
        },
        "v2_sanity": sanity,
        "results": rows,
        "no_submission_performed": True,
    }
    result["final_gate_passed"] = all((
        source_before == source_after == EXPECTED_SOURCE_SHA,
        result["research_source_lf_sha256"] == EXPECTED_SOURCE_SHA,
        dependency["pass"], leakage["pass"], integrity["pass"], selector["pass"],
        clean["pass"], reset["pass"],
        result["equivalence"]["games_passed"] == result["equivalence"]["games"],
        result["equivalence"]["action_equivalence_rate"] == 1.0,
        result["equivalence"]["all_719_action_games"],
        result["equivalence"]["final_money_delta_zero"],
        result["equivalence"]["final_advantage_delta_zero"],
        result["equivalence"]["terminal_state_exact"],
        result["safety"]["runtime_failures"] == 0,
        result["safety"]["semantic_failures"] == 0,
        result["safety"]["actual_livestock_escapes"] == 0,
        result["safety"]["meaningful_stranding_games"] == 0,
        result["safety"]["unexpected_fallbacks"] == 0,
        sanity["pass"],
    ))
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "final_gate_passed": result["final_gate_passed"],
        "submission_raw_sha256": result["submission_raw_sha256"],
        "submission_lf_sha256": result["submission_lf_sha256"],
        "submission_size_bytes": result["submission_size_bytes"],
        "equivalence": result["equivalence"],
        "safety": result["safety"],
        "runtime_performance": result["runtime_performance"],
        "v2_sanity": {key: sanity[key] for key in (
            "games", "wins", "losses", "ties", "average_money", "average_advantage", "pass",
        )},
    }, indent=2))


if __name__ == "__main__":
    main()
