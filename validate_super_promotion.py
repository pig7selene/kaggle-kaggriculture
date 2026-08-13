"""Verify the named promoted wrapper is action-equivalent to its raw finalist."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from run_epic_experiments import _independent_shop_schedule, _run_with_fixed_shops
from run_v27_replay_backbone import _inventory_value, _semantic_validate


ROOT = Path(__file__).resolve().parent
RAW = "agents/super_replay/super_raw_55459817.py"
PROMOTED = "agents/super_replay/super_backbone_v1.py"
K3 = "agents/v27_replay_weed_guard.py"
OUTPUT = ROOT / "experiments/super_replay_promotion_validation.json"


def _run(candidate_path, seed, seat):
    requested = []
    errors = []
    candidate = run_path(str(ROOT / candidate_path))["agent"]
    rival = run_path(str(ROOT / K3))["agent"]

    def checked(obs):
        action = candidate(obs)
        requested.append(deepcopy(action))
        try:
            _semantic_validate(obs, action)
        except Exception as error:
            errors.append({"step": int(obs["step"]), "error": repr(error)})
        return action

    agents = [rival, rival]
    agents[seat] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    runtime = None
    try:
        _run_with_fixed_shops(env, agents, _independent_shop_schedule(seed))
    except Exception as error:
        runtime = repr(error)
    final = env.steps[-1]
    stranded_value, stranded = _inventory_value(final[seat])
    telemetry = deepcopy(candidate.telemetry)
    return {
        "requested": requested, "runtime_error": runtime, "semantic_failures": errors,
        "steps": len(env.steps), "final_money": float(final[seat].reward),
        "opponent_money": float(final[1 - seat].reward),
        "stranded_value": stranded_value, "stranded": stranded,
        "route_execution": {
            "requested": telemetry["all_route_requests"],
            "executed_unmodified": telemetry["all_route_matches"],
            "mismatched_or_corrected": telemetry["all_route_requests"] - telemetry["all_route_matches"],
            "weed_repairs": telemetry["repairs"]["weed"],
            "repair_success": telemetry["repair_success"],
            "repair_abort": telemetry["repair_abort"],
            "dropped_route_actions": telemetry["dropped_route_actions"],
            "extra_worker_passes": telemetry["extra_worker_passes"],
            "fallback_step": telemetry["fallback_step"],
        },
    }


def main():
    rows = []
    for seed, seat in ((997100, 0), (997101, 1)):
        raw = _run(RAW, seed, seat)
        promoted = _run(PROMOTED, seed, seat)
        differences = [index for index, (left, right) in enumerate(zip(raw["requested"], promoted["requested"])) if left != right]
        rows.append({
            "seed": seed, "seat": seat, "compared_actions": min(len(raw["requested"]), len(promoted["requested"])),
            "action_differences": differences, "raw": {key: value for key, value in raw.items() if key != "requested"},
            "promoted": {key: value for key, value in promoted.items() if key != "requested"},
        })
    OUTPUT.write_text(json.dumps({
        "schema_version": 1, "raw": RAW, "promoted": PROMOTED, "games": rows,
        "passed": all(row["compared_actions"] == 719 and not row["action_differences"] and row["raw"] == row["promoted"] for row in rows),
    }, indent=2, sort_keys=True) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
