"""Capability gate for the day-0-reserved end-to-end route owner.

The first pass proves that the owner wrapper is exactly equivalent to the
frozen route.  A second pass enables one small wheat lifecycle using only the
capacity reserved before day 10.  Both passes use complete deterministic
episodes, fresh module instances, both seats, and strict action validation.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics

from kaggle_environments import make

from run_checkpoint_executor_resume import _validate, _terminal_value
ROOT = Path(__file__).resolve().parent
BASELINE = "agents/top50_distilled/top50_observable_portfolio.py"
OWNER = "agents/autonomous_next/end_to_end_owner_v1.py"
CANDIDATE = "agents/autonomous_next/end_to_end_owner_crop_v1.py"
UNIT_OPS = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER", "HARVEST",
    "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "PICKUP", "DROP",
    "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER",
}


def _load(path: str, tag: str):
    absolute = (ROOT / path).resolve()
    name = f"e2e_{tag}_{hashlib.sha256(str(absolute).encode()).hexdigest()[:12]}"
    spec = importlib.util.spec_from_file_location(name, absolute)
    if spec is None or spec.loader is None:
        raise ImportError(absolute)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _animals(obs, seat):
    farm = obs["farms"][seat]
    return {
        (x, y): tile
        for y, row in enumerate(farm.get("tiles", []))
        for x, tile in enumerate(row)
        if isinstance(tile, dict) and tile.get("animal")
    }


def _inventory_value(obs, seat):
    if int(obs.get("player", seat)) != int(seat):
        return 0.0
    private = obs.get("private", {})
    prices = obs.get("market", {}).get("prices", {})
    valid = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"}
    total = 0.0
    for item, quantity in private.get("shed", {}).items():
        if item in valid:
            total += int(quantity) * float(prices.get(item, 1))
    for inv in private.get("inventories", []):
        for item, quantity in inv.items():
            if item in valid:
                total += int(quantity) * float(prices.get(item, 1))
    return total


def _strict_validate(obs, action):
    """Validate the exact public action schema.

    The simulator deliberately permits silent no-ops (for example a replay
    route may issue a stale WATER while another unit has already serviced the
    tile).  Treating those as hard semantic failures would incorrectly reject
    an otherwise completed inherited route, so runtime completion is the
    semantic oracle and this function checks only malformed actions/cardinality.
    """
    errors = []
    try:
        _validate(obs, action)
    except Exception as exc:
        errors.append(f"schema:{exc!r}")
        return errors
    return errors


def _run(path, opponent_path, seed, seat):
    own = _load(path, f"own_{seed}_{seat}_{Path(path).stem}")
    opponent = _load(opponent_path, f"opp_{seed}_{seat}_{Path(opponent_path).stem}")
    history = []
    semantic = []

    def controlled(obs):
        action = own.agent(obs)
        history.append(deepcopy(action))
        errors = _strict_validate(obs, action)
        if errors:
            semantic.append({"step": int(obs.get("step", -1)), "errors": errors, "action": deepcopy(action)})
        return action

    pair = [opponent.agent, opponent.agent]
    pair[int(seat)] = controlled
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime = None
    try:
        env.run(pair)
    except Exception as exc:
        runtime = repr(exc)
    if runtime or len(getattr(env, "steps", [])) != 720:
        return {
            "path": path, "seed": int(seed), "seat": int(seat),
            "runtime_error": runtime or f"steps={len(getattr(env, 'steps', []))}",
            "semantic_failures": semantic, "actions": history,
        }
    final = env.steps[-1]
    own_money = float(final[int(seat)].reward)
    opp_money = float(final[1 - int(seat)].reward)
    initial_animals = _animals(env.steps[0][seat].observation, seat)
    lost = []
    for step_state in env.steps:
        visible = _animals(step_state[seat].observation, seat)
        for position, tile in initial_animals.items():
            if position not in visible:
                event = {"step": int(step_state[seat].observation.get("step", -1)), "position": list(position), "animal": tile.get("animal")}
                if event not in lost:
                    lost.append(event)
    telemetry = deepcopy(getattr(own, "telemetry", {}))
    return {
        "path": path, "seed": int(seed), "seat": int(seat), "runtime_error": None,
        "semantic_failures": semantic, "actions": history,
        "own_money": own_money, "opponent_money": opp_money, "advantage": own_money - opp_money,
        "animal_loss": bool(lost), "animal_loss_events": lost,
        "terminal_inventory_value": _inventory_value(final[int(seat)].observation, seat),
        "telemetry": telemetry,
        "steps": len(env.steps),
    }


def _equivalence(seeds):
    rows = []
    for seed in seeds:
        for seat in (0, 1):
            base = _run(BASELINE, BASELINE, seed, seat)
            owner = _run(OWNER, BASELINE, seed, seat)
            compared = min(len(base.get("actions", [])), len(owner.get("actions", [])))
            mismatches = sum(base["actions"][i] != owner["actions"][i] for i in range(compared))
            rows.append({
                "seed": int(seed), "seat": int(seat), "actions_compared": compared,
                "mismatches": mismatches,
                "base_money": base.get("own_money"), "owner_money": owner.get("own_money"),
                "base_runtime": base.get("runtime_error"), "owner_runtime": owner.get("runtime_error"),
                "base_semantic": len(base.get("semantic_failures", [])),
                "owner_semantic": len(owner.get("semantic_failures", [])),
            })
    return rows


def _candidate_screen(seeds):
    rows = []
    for seed in seeds:
        for seat in (0, 1):
            base = _run(BASELINE, BASELINE, seed, seat)
            candidate = _run(CANDIDATE, BASELINE, seed, seat)
            row = {
                "seed": int(seed), "seat": int(seat), "baseline": base, "candidate": candidate,
            }
            if base.get("own_money") is not None and candidate.get("own_money") is not None:
                row["own_money_delta"] = candidate["own_money"] - base["own_money"]
                row["advantage_delta"] = candidate["advantage"] - base["advantage"]
            rows.append(row)
    return rows


def _summary(rows):
    valid = [r for r in rows if "own_money_delta" in r]
    deltas = [float(r["own_money_delta"]) for r in valid]
    cand = [r["candidate"] for r in valid]
    return {
        "conditions": len(rows), "valid": len(valid),
        "runtime_failures": sum(bool(r["candidate"].get("runtime_error") or r["baseline"].get("runtime_error")) for r in rows),
        "semantic_failures": sum(len(r["candidate"].get("semantic_failures", [])) + len(r["baseline"].get("semantic_failures", [])) for r in rows),
        "animal_loss_conditions": sum(bool(r["candidate"].get("animal_loss")) for r in valid),
        "terminal_stranding_conditions": sum(float(r["candidate"].get("terminal_inventory_value", 0.0)) > 0 for r in valid),
        "mean_baseline_money": statistics.fmean(r["baseline"]["own_money"] for r in valid) if valid else None,
        "mean_candidate_money": statistics.fmean(r["candidate"]["own_money"] for r in valid) if valid else None,
        "mean_own_money_delta": statistics.fmean(deltas) if deltas else None,
        "median_own_money_delta": statistics.median(deltas) if deltas else None,
        "p10_own_money_delta": sorted(deltas)[max(0, int((len(deltas) - 1) * 0.10))] if deltas else None,
        "mean_advantage_delta": statistics.fmean(float(r["advantage_delta"]) for r in valid) if valid else None,
        "admissions": sum(int(r["candidate"].get("telemetry", {}).get("admissions", 0)) for r in valid),
        "plant_actions": sum(int(r["candidate"].get("telemetry", {}).get("plant_actions", 0)) for r in valid),
        "harvest_actions": sum(int(r["candidate"].get("telemetry", {}).get("harvest_actions", 0)) for r in valid),
        "sell_requests": sum(int(r["candidate"].get("telemetry", {}).get("sell_requests", 0)) for r in valid),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[57400, 57401, 57402, 57403])
    parser.add_argument("--output", default="experiments/end_to_end_owner_screen.json")
    args = parser.parse_args()
    eq = _equivalence(args.seeds[:2])
    screen = _candidate_screen(args.seeds)
    payload = {
        "schema_version": 1,
        "design": "complete route owner equivalence then one pre-day-10 reserved wheat lifecycle",
        "baseline": BASELINE, "owner_control": OWNER, "candidate": CANDIDATE,
        "seeds": [int(s) for s in args.seeds], "equivalence": eq,
        "candidate_rows": screen, "candidate_summary": _summary(screen),
    }
    output = (ROOT / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    print(json.dumps({"equivalence": eq, "candidate_summary": payload["candidate_summary"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
