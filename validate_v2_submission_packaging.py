"""Packaging-only differential validation for Super Replay Backbone V2."""

from __future__ import annotations

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
import argparse

import validate_v27_submission as harness


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "agents/super_replay_v2/super_backbone_v2.py"
SUBMISSION = ROOT / "submission/main.py"
OUTPUT = ROOT / "experiments/v2_submission_packaging.json"
EXPECTED_SOURCE_SHA = "c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef"
ROUTE_ID = "super_raw_55463387"
SOURCE_REPLAY = "experiments/v2_top20_corpus/replays/episode-92468241-replay.json"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _trace(path, player):
    return f"trace:{ROOT / path}:{int(player)}"


def _conditions():
    replay = json.loads((ROOT / SOURCE_REPLAY).read_text())
    rows = [{
        "name": "jalkarna_source_92468241",
        "group": "source_replay",
        "seed": int(replay["info"]["seed"]),
        "seat": 1,
        "opponent": "recorded_trace",
        "opponent_spec": _trace(SOURCE_REPLAY, 0),
        "schedule": harness._recorded_shop_schedule(replay),
        "config": {},
    }]

    fresh_opponents = [
        ("V1", "agents/super_replay/super_backbone_v1.py"),
        ("K3", "agents/v27_replay_weed_guard.py"),
        ("JALKARNA_raw", "agents/super_replay_v2/v2_raw_55463387.py"),
        ("Nazmus_raw", "agents/super_replay_v2/v2_raw_55445174.py"),
    ]
    for index, seed in enumerate(range(999100, 999108)):
        opponent, spec = fresh_opponents[index % len(fresh_opponents)]
        for seat in (0, 1):
            rows.append({
                "name": f"fresh_{seed}_s{seat}_{opponent}",
                "group": "fresh",
                "seed": seed,
                "seat": seat,
                "opponent": opponent,
                "opponent_spec": spec,
                "schedule": None,
                "config": {},
            })

    strong = [
        ("V1", "agents/super_replay/super_backbone_v1.py"),
        ("K3", "agents/v27_replay_weed_guard.py"),
        ("JALKARNA_raw", "agents/super_replay_v2/v2_raw_55463387.py"),
        ("Nazmus_raw", "agents/super_replay_v2/v2_raw_55445174.py"),
        ("adaptive_rank1", "agents/super_replay_v2/v2_raw_55440039.py"),
    ]
    for index, (opponent, spec) in enumerate(strong):
        for seat in (0, 1):
            rows.append({
                "name": f"strong_{opponent}_s{seat}",
                "group": "strong",
                "seed": 999300 + index,
                "seat": seat,
                "opponent": opponent,
                "opponent_spec": spec,
                "schedule": None,
                "config": {},
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
        "weed_important_segments": [
            {"label": "early_route", "min_step": 120, "unit": None},
            {"label": "mid_route", "min_step": 300, "unit": None},
        ],
    }
    for index, (name, injections) in enumerate(weed_cases.items()):
        rows.append({
            "name": name,
            "group": "weed",
            "seed": 999500 + index,
            "seat": index % 2,
            "opponent": "V1",
            "opponent_spec": "agents/super_replay/super_backbone_v1.py",
            "schedule": None,
            "config": {"weedSpawnChance": 0},
            "injections": injections,
        })
    return rows


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
env=make("kaggriculture",configuration={"episodeSteps":720,"seed":999999},debug=True); env.run([checked,"starter"])
f=env.steps[-1]
print(json.dumps({"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"calls":len(values),"steps":len(env.steps),"statuses":[x.status for x in f],"money":[x.reward for x in f],"import_ms":import_ms,"first_call_ms":values[0],"average_call_ms":sum(values)/len(values),"median_call_ms":sorted(values)[len(values)//2],"max_call_ms":max(values),"peak_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}))
'''
    with tempfile.TemporaryDirectory(prefix="v2-standalone-") as raw:
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
        payload["directory_contents_before_cleanup"] = sorted(p.name for p in directory.iterdir())
        payload["pass"] = (
            payload["sha256"] == _sha256(SUBMISSION)
            and payload["calls"] == 719
            and payload["steps"] == 720
            and payload["statuses"] == ["DONE", "DONE"]
        )
        return payload


def _run_pair_configured(condition):
    """Set frozen V2 paths inside each isolated validation worker."""
    harness.SOURCE = SOURCE
    harness.SUBMISSION = SUBMISSION
    harness.EXPECTED_SOURCE_SHA = EXPECTED_SOURCE_SHA
    harness.ROUTE_ID = ROUTE_ID
    return harness._run_pair(condition)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition-index", type=int)
    parser.add_argument("--condition-output")
    args = parser.parse_args()
    if args.condition_index is not None:
        if not args.condition_output:
            raise SystemExit("--condition-output is required")
        result = _run_pair_configured(_conditions()[args.condition_index])
        Path(args.condition_output).write_text(json.dumps(result, separators=(",", ":")))
        return

    if _sha256(SOURCE) != EXPECTED_SOURCE_SHA:
        raise SystemExit("frozen V2 source hash mismatch")

    harness.SOURCE = SOURCE
    harness.SUBMISSION = SUBMISSION
    harness.OUTPUT = OUTPUT
    harness.EXPECTED_SOURCE_SHA = EXPECTED_SOURCE_SHA
    harness.ROUTE_ID = ROUTE_ID
    harness._conditions = _conditions

    # Isolated workers release the large research-side route-bank imports after
    # each pair. The packaged agent itself never imports those banks.
    conditions = _conditions()
    rows = []
    source_before = _sha256(SOURCE)
    with tempfile.TemporaryDirectory(prefix="v2-package-pairs-") as raw:
        directory = Path(raw)
        for index, condition in enumerate(conditions):
            target = directory / f"{index}.json"
            completed = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()),
                 "--condition-index", str(index), "--condition-output", str(target)],
                cwd=ROOT, text=True, capture_output=True, timeout=240,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )
            if completed.returncode:
                raise RuntimeError(
                    f"condition {condition['name']} failed: {completed.stderr or completed.stdout}"
                )
            result = json.loads(target.read_text())
            rows.append(result)
            print(f"{result['name']}: {'PASS' if result['equivalent'] else 'FAIL'}", flush=True)
    order = {row["name"]: index for index, row in enumerate(conditions)}
    rows.sort(key=lambda row: order[row["name"]])

    source_after = _sha256(SOURCE)
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
        "farmer_actions_sha256": _digest([r["farmer"] for r in source_route["consensus_actions"]]),
        "worker_actions_sha256": _digest([r["hands"] for r in source_route["consensus_actions"]]),
        "market_actions_sha256": _digest([r["market"] for r in source_route["consensus_actions"]]),
        "exact_payload_equal": (
            source_route["route_id"] == submission_route["route_id"]
            and source_route["consensus_actions"] == submission_route["consensus_actions"]
            and source_route["expected_state"] == submission_route["expected_state"]
        ),
    }
    package_runs = [row["submission"] for row in rows]
    source_runs = [row["source"] for row in rows]
    package_matches = sum(r["telemetry_final"]["route"][0] for r in package_runs)
    package_requests = sum(r["telemetry_final"]["route"][1] for r in package_runs)
    source_matches = sum(r["telemetry_final"]["route"][0] for r in source_runs)
    source_requests = sum(r["telemetry_final"]["route"][1] for r in source_runs)
    clean = _clean_performance_probe()
    dependency = harness._dependency_audit()
    result = {
        "source": str(SOURCE.relative_to(ROOT)),
        "submission": str(SUBMISSION.relative_to(ROOT)),
        "source_expected_sha256": EXPECTED_SOURCE_SHA,
        "source_sha256_before": source_before,
        "source_sha256_after": source_after,
        "previous_submission_sha256": "0b7c4fb3587f446a414cad30464522dab68ac64d88bc8f4e776e090e9b4cf1d8",
        "submission_sha256": _sha256(SUBMISSION),
        "submission_size_bytes": SUBMISSION.stat().st_size,
        "current_best_sha256": _sha256(ROOT / "experiments/current_best.json"),
        "dependency_audit": dependency,
        "dependency_graph": [
            "agents/super_replay_v2/super_backbone_v2.py",
            "agents/super_replay_v2/backbone_common.py",
            "experiments/v2_route_executor.json:super_raw_55463387",
            "agents/v27_backbone_common.py:make_v27_agent(stage=3)",
            "stdlib base64/json/zlib/copy + installed kaggle_environments game constants",
        ],
        "route_payload_audit": route_audit,
        "strategy_modules_enabled": {
            "worker_rematching": True,
            "bounded_worker_weed_repair": True,
            "capital_repair": False,
            "hire_heuristic": False,
            "animal_survival_override": False,
            "sell_reordering": False,
            "fallback": False,
        },
        "condition_count": len(rows),
        "actual_game_count": len(rows) * 2 + 1,
        "groups": {
            group: {
                "pairs": sum(r["group"] == group for r in rows),
                "passed": sum(r["group"] == group and r["equivalent"] for r in rows),
            }
            for group in ("source_replay", "fresh", "strong", "weed")
        },
        "all_equivalent": all(r["equivalent"] for r in rows),
        "semantic_failures": sum(len(r["source"]["semantic_failures"]) + len(r["submission"]["semantic_failures"]) for r in rows),
        "runtime_failures": sum(bool(r["source"]["runtime_error"] or r["submission"]["runtime_error"]) for r in rows),
        "livestock_escapes": sum(len(r["submission"]["livestock_escapes"]) for r in rows),
        "packaging_induced_livestock_regressions": sum(r["source"]["livestock_escapes"] != r["submission"]["livestock_escapes"] for r in rows),
        "meaningful_stranding_threshold": 500,
        "meaningful_stranding_games": sum(r["submission"]["stranded_value"] > 500 for r in rows),
        "packaging_induced_stranding_regressions": sum(r["source"]["stranded_value"] != r["submission"]["stranded_value"] for r in rows),
        "unexpected_fallbacks": sum(r["submission"]["telemetry_final"]["fallback_step"] is not None for r in rows),
        "route_fidelity": {
            "source_matches": source_matches,
            "source_requests": source_requests,
            "source_percent": 100 * source_matches / source_requests,
            "submission_matches": package_matches,
            "submission_requests": package_requests,
            "submission_percent": 100 * package_matches / package_requests,
            "delta_percentage_points": 100 * (package_matches / package_requests - source_matches / source_requests),
        },
        "clean_directory_test": clean,
        "performance": {
            "clean_standalone": clean,
            "validator_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        "results": rows,
    }
    result["final_gate_passed"] = all((
        source_before == EXPECTED_SOURCE_SHA,
        source_after == EXPECTED_SOURCE_SHA,
        result["all_equivalent"],
        dependency["pass"],
        clean["pass"],
        route_audit["exact_payload_equal"],
        route_audit["steps"] == 719,
        result["runtime_failures"] == 0,
        result["semantic_failures"] == 0,
        result["route_fidelity"]["delta_percentage_points"] == 0,
        result["packaging_induced_livestock_regressions"] == 0,
        result["packaging_induced_stranding_regressions"] == 0,
        result["unexpected_fallbacks"] == 0,
    ))
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "final_gate_passed": result["final_gate_passed"],
        "groups": result["groups"],
        "route_payload_audit": route_audit,
        "submission_sha256": result["submission_sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
