"""Packaging-only differential validation for Super Replay Backbone v1."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
from runpy import run_path
import shutil
import subprocess
import sys
import tempfile

import validate_v27_submission as harness


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "agents/super_replay/super_backbone_v1.py"
SUBMISSION = ROOT / "submission/main.py"
OUTPUT = ROOT / "experiments/super_backbone_submission_packaging.json"
EXPECTED_SOURCE_SHA = "96bd9cefd7c31075e47719ec1f9d1ee9391b467f68b956c65e0dd96478adb516"
ROUTE_ID = "super_raw_55459817"
_HARNESS_RUN_PAIR = harness._run_pair


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _trace(path, player):
    return f"trace:{ROOT / path}:{int(player)}"


def _conditions():
    source_path = "experiments/super_replay_corpus/replays/episode-92368798-replay.json"
    source_replay = json.loads((ROOT / source_path).read_text())
    rows = [{
        "name": "ricardo_source_92368798", "group": "source_replay",
        "seed": int(source_replay["info"]["seed"]), "seat": 1,
        "opponent": "recorded_trace", "opponent_spec": _trace(source_path, 0),
        "schedule": harness._recorded_shop_schedule(source_replay), "config": {},
    }]

    fresh_opponents = [
        ("K3", "agents/v27_replay_weed_guard.py"),
        ("family2", "agents/super_replay/super_family_02_medoid.py"),
        ("frozen_803", "agents/opening_public_front_cow8_day6.py"),
        ("R3", "agents/leaderboard_r3_cow6_capital.py"),
    ]
    for index, seed in enumerate(range(998100, 998108)):
        opponent, spec = fresh_opponents[index % len(fresh_opponents)]
        for seat in (0, 1):
            rows.append({
                "name": f"fresh_{seed}_s{seat}_{opponent}", "group": "fresh",
                "seed": seed, "seat": seat, "opponent": opponent,
                "opponent_spec": spec, "schedule": None, "config": {},
            })

    local = [
        ("K3", "agents/v27_replay_weed_guard.py"),
        ("frozen_803", "agents/opening_public_front_cow8_day6.py"),
        ("R3", "agents/leaderboard_r3_cow6_capital.py"),
        ("lifecycle", "agents/lifecycle_lc_combined.py"),
        ("family2", "agents/super_replay/super_family_02_medoid.py"),
        ("ricardo_raw", "agents/super_replay/super_raw_55459817.py"),
    ]
    for index, (opponent, spec) in enumerate(local):
        for seat in (0, 1):
            rows.append({
                "name": f"strong_{opponent}_s{seat}", "group": "strong",
                "seed": 998300 + index, "seat": seat, "opponent": opponent,
                "opponent_spec": spec, "schedule": None, "config": {},
            })

    routes = [
        ("family1_trace", "experiments/super_replay_corpus/replays/episode-92391343-replay.json", 1),
        ("family2_trace", "experiments/super_replay_corpus/replays/episode-92376386-replay.json", 0),
        ("family3_trace", "experiments/super_replay_corpus/replays/episode-92367083-replay.json", 0),
    ]
    for opponent, path, player in routes:
        replay = json.loads((ROOT / path).read_text())
        for seat in (0, 1):
            rows.append({
                "name": f"strong_{opponent}_s{seat}", "group": "strong",
                "seed": int(replay["info"]["seed"]), "seat": seat,
                "opponent": opponent, "opponent_spec": _trace(path, player),
                "schedule": harness._recorded_shop_schedule(replay), "config": {},
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
        "weed_economic_sequence": [
            {"label": "near_first_land", "min_step": 145, "unit": None},
            {"label": "near_second_land", "min_step": 235, "unit": None},
        ],
    }
    for index, (name, injections) in enumerate(weed_cases.items()):
        rows.append({
            "name": name, "group": "weed", "seed": 998500 + index,
            "seat": index % 2, "opponent": "K3",
            "opponent_spec": "agents/v27_replay_weed_guard.py", "schedule": None,
            "config": {"weedSpawnChance": 0}, "injections": injections,
        })
    return rows


def _run_pair_configured(condition):
    """Configure spawned workers before delegating to the shared harness."""
    harness.SOURCE = SOURCE
    harness.SUBMISSION = SUBMISSION
    harness.EXPECTED_SOURCE_SHA = EXPECTED_SOURCE_SHA
    harness.ROUTE_ID = ROUTE_ID
    return _HARNESS_RUN_PAIR(condition)


def _clean_performance_probe():
    script = r'''import hashlib,json,resource,time
from pathlib import Path
from runpy import run_path
from kaggle_environments import make
p=Path("main.py")
t=time.perf_counter_ns(); a=run_path(str(p))["agent"]; import_ms=(time.perf_counter_ns()-t)/1e6
values=[]
def checked(obs):
 t=time.perf_counter_ns(); out=a(obs); values.append((time.perf_counter_ns()-t)/1e6); return out
env=make("kaggriculture",configuration={"episodeSteps":720,"seed":997999},debug=True); env.run([checked,"starter"])
f=env.steps[-1]
print(json.dumps({"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"calls":len(values),"steps":len(env.steps),"statuses":[x.status for x in f],"money":[x.reward for x in f],"import_ms":import_ms,"first_call_ms":values[0],"average_call_ms":sum(values)/len(values),"median_call_ms":sorted(values)[len(values)//2],"max_call_ms":max(values),"peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
'''
    with tempfile.TemporaryDirectory(prefix="super-backbone-standalone-") as raw:
        directory = Path(raw)
        shutil.copy2(SUBMISSION, directory / "main.py")
        completed = subprocess.run(
            [sys.executable, "-c", script], cwd=directory, text=True,
            capture_output=True, timeout=180,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        if completed.returncode:
            return {"pass": False, "returncode": completed.returncode,
                    "stdout": completed.stdout, "stderr": completed.stderr}
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
        payload["directory_contents_before_cleanup"] = sorted(value.name for value in directory.iterdir())
        payload["pass"] = (
            payload["sha256"] == hashlib.sha256(SUBMISSION.read_bytes()).hexdigest()
            and payload["calls"] == 719 and payload["steps"] == 720
            and payload["statuses"] == ["DONE", "DONE"]
        )
        return payload


def main():
    harness.SOURCE = SOURCE
    harness.SUBMISSION = SUBMISSION
    harness.OUTPUT = OUTPUT
    harness.EXPECTED_SOURCE_SHA = EXPECTED_SOURCE_SHA
    harness.ROUTE_ID = ROUTE_ID
    harness._conditions = _conditions
    harness._run_pair = _run_pair_configured
    original_clean_directory_test = harness._clean_directory_test
    harness._clean_directory_test = lambda: {"pass": True, "superseded_by": "clean_standalone performance probe"}
    harness.main()
    harness._clean_directory_test = original_clean_directory_test

    result = json.loads(OUTPUT.read_text())
    source_agent = run_path(str(SOURCE))["agent"]
    submission_agent = run_path(str(SUBMISSION))["agent"]
    source_route = source_agent.route
    submission_route = submission_agent.route
    route_audit = {
        "route_id": ROUTE_ID,
        "steps": len(source_route["consensus_actions"]),
        "expected_state_steps": len(source_route["expected_state"]),
        "actions_sha256_source": _digest(source_route["consensus_actions"]),
        "actions_sha256_submission": _digest(submission_route["consensus_actions"]),
        "expected_state_sha256_source": _digest(source_route["expected_state"]),
        "expected_state_sha256_submission": _digest(submission_route["expected_state"]),
        "farmer_actions_sha256": _digest([row["farmer"] for row in source_route["consensus_actions"]]),
        "worker_actions_sha256": _digest([row["hands"] for row in source_route["consensus_actions"]]),
        "market_actions_sha256": _digest([row["market"] for row in source_route["consensus_actions"]]),
        "exact_payload_equal": (
            source_route["route_id"] == submission_route["route_id"]
            and source_route["consensus_actions"] == submission_route["consensus_actions"]
            and source_route["expected_state"] == submission_route["expected_state"]
        ),
    }
    result["route_payload_audit"] = route_audit
    result["dependency_graph"] = [
        "agents/super_replay/super_backbone_v1.py",
        "agents/super_replay/super_backbone_common.py",
        "experiments/super_replay_route_executor.json:super_raw_55459817",
        "agents/v27_backbone_common.py:make_v27_agent(stage=3)",
        "stdlib base64/json/zlib/copy + installed kaggle_environments game constants",
    ]
    result["strategy_modules_enabled"] = {
        "worker_rematching": True, "bounded_worker_weed_repair": True,
        "capital_repair": False, "hire_heuristic": False,
        "animal_survival_override": False, "sell_reordering": False,
        "fallback": False,
    }
    result["packaging_induced_livestock_regressions"] = sum(
        row["source"]["livestock_escapes"] != row["submission"]["livestock_escapes"]
        for row in result["results"]
    )
    result["packaging_induced_stranding_regressions"] = sum(
        row["source"]["stranded_value"] != row["submission"]["stranded_value"]
        for row in result["results"]
    )
    result["clean_directory_test"] = _clean_performance_probe()
    result["performance"]["clean_standalone"] = result["clean_directory_test"]
    result["performance"]["validator_peak_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result["final_gate_passed"] = all((
        result["source_sha256_before"] == EXPECTED_SOURCE_SHA,
        result["source_sha256_after"] == EXPECTED_SOURCE_SHA,
        result["all_equivalent"], result["dependency_audit"]["pass"],
        result["clean_directory_test"]["pass"], route_audit["exact_payload_equal"],
        route_audit["steps"] == 719, result["runtime_failures"] == 0,
        result["semantic_failures"] == 0,
        result["route_fidelity"]["delta_percentage_points"] == 0,
        result["packaging_induced_livestock_regressions"] == 0,
        result["packaging_induced_stranding_regressions"] == 0,
        all(row["submission"]["telemetry_final"]["fallback_step"] is None for row in result["results"]),
    ))
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "final_gate_passed": result["final_gate_passed"],
        "groups": result["groups"], "route_payload_audit": route_audit,
        "submission_sha256": result["submission_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
