"""Resume-gate harness for the commitment-first checkpoint executor.

Each condition runs a fresh CurrentBest continuation and a fresh game where
the executor takes over exactly at a checkpoint.  The state is never edited;
the candidate only receives the real observation produced by the simulator.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics

from kaggle_environments import make


ROOT = Path(__file__).resolve().parent
BASELINE_PATH = "agents/top50_distilled/top50_observable_portfolio.py"
EXECUTOR_PATH = "agents/checkpoint_executor/commitment_executor_v1.py"
OPPONENTS = {"current_best": BASELINE_PATH}
UNIT_OPS = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER", "HARVEST",
    "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "PICKUP", "DROP",
    "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER",
}
MARKET_OPS = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}


def _load(path, tag):
    absolute = (ROOT / path).resolve()
    name = f"checkpoint_{tag}_{hashlib.sha256(str(absolute).encode()).hexdigest()[:12]}"
    spec = importlib.util.spec_from_file_location(name, absolute)
    if spec is None or spec.loader is None:
        raise ImportError(absolute)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def _validate(obs, action):
    if not isinstance(action, dict) or set(action) != {"farmer", "hands", "market"}:
        raise AssertionError("schema")
    if not isinstance(action["farmer"], list) or not action["farmer"] or action["farmer"][0] not in UNIT_OPS:
        raise AssertionError("farmer")
    hands = action["hands"]
    expected = len(obs["farms"][obs["player"]].get("hands", []))
    if not isinstance(hands, list) or len(hands) != expected:
        raise AssertionError(f"hands {len(hands) if isinstance(hands, list) else 'bad'} != {expected}")
    for value in hands:
        if not isinstance(value, list) or not value or value[0] not in UNIT_OPS:
            raise AssertionError("hand")
    market = action["market"]
    if not isinstance(market, list) or len(market) > 10:
        raise AssertionError("market")
    for order in market:
        if not isinstance(order, list) or not order or order[0] not in MARKET_OPS:
            raise AssertionError("order")
        if order[0] in {"HIRE", "BUY_LAND"}:
            if len(order) != 1:
                raise AssertionError("order arity")
        elif len(order) != 3 or not isinstance(order[2], int) or order[2] <= 0:
            raise AssertionError("order quantity")


def _animal_count(state, seat):
    farm = state.observation["farms"][seat]
    total = 0
    for row in farm.get("tiles", []):
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal"):
                total += 1
    private = state.observation.get("private", {}) if seat == int(state.observation.get("player", seat)) else {}
    total += sum(int(private.get("shed", {}).get(a, 0)) for a in ("GOOSE", "COW", "SHEEP"))
    total += sum(sum(int(inv.get(a, 0)) for inv in private.get("inventories", [])) for a in ("GOOSE", "COW", "SHEEP"))
    return total


def _terminal_value(state, seat):
    obs = state.observation
    private = obs.get("private", {})
    prices = obs.get("market", {}).get("prices", {})
    total = 0.0
    for item, quantity in private.get("shed", {}).items():
        if item not in {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"}:
            continue
        total += int(quantity) * float(prices.get(item, 1))
    for inv in private.get("inventories", []):
        for item, quantity in inv.items():
            if item in {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"}:
                total += int(quantity) * float(prices.get(item, 1))
    return total


def _run_once(path, opponent_path, seed, seat, checkpoint=None):
    base = _load(BASELINE_PATH, f"base_{seed}_{seat}_{checkpoint}")
    opponent = _load(opponent_path, f"opp_{seed}_{seat}_{checkpoint}")
    executor = _load(path, f"exec_{seed}_{seat}_{checkpoint}") if checkpoint is not None else None
    semantic = []
    calls = 0

    def controlled(obs):
        nonlocal calls
        calls += 1
        if checkpoint is not None and int(obs.get("step", 0)) >= int(checkpoint):
            action = executor(obs)
        else:
            action = base(obs)
        try:
            _validate(obs, action)
        except Exception as exc:
            semantic.append({"step": int(obs.get("step", -1)), "error": repr(exc), "action": deepcopy(action)})
        return action

    pair = [opponent, opponent]
    pair[int(seat)] = controlled
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime = None
    try:
        env.run(pair)
    except Exception as exc:
        runtime = repr(exc)
    if runtime or len(getattr(env, "steps", [])) != 720:
        return {"seed": int(seed), "seat": int(seat), "checkpoint": checkpoint, "runtime_error": runtime or f"steps={len(getattr(env, 'steps', []))}", "semantic_failures": semantic, "calls": calls}
    final = env.steps[-1]
    own = float(final[int(seat)].reward)
    rival = float(final[1 - int(seat)].reward)
    counts = [_animal_count(step_states[int(seat)], int(seat)) for step_states in env.steps]
    telemetry = getattr(executor, "telemetry", {}) if executor is not None else {}
    return {
        "seed": int(seed), "seat": int(seat), "checkpoint": checkpoint, "runtime_error": None,
        "semantic_failures": semantic, "calls": calls, "own_money": own, "opponent_money": rival,
        "advantage": own - rival, "animal_max": max(counts), "animal_final": counts[-1],
        "animal_loss": counts[-1] < max(counts), "terminal_value": _terminal_value(final[int(seat)], int(seat)),
        "telemetry": deepcopy(telemetry),
    }


def _job(job):
    seed, seat, checkpoint = job
    control = _run_once(BASELINE_PATH, BASELINE_PATH, seed, seat, checkpoint=None)
    resumed = _run_once(EXECUTOR_PATH, BASELINE_PATH, seed, seat, checkpoint=checkpoint)
    resumed["control_own_money"] = control.get("own_money")
    resumed["control_opponent_money"] = control.get("opponent_money")
    resumed["control_advantage"] = control.get("advantage")
    resumed["own_money_gap"] = resumed.get("own_money", 0.0) - control.get("own_money", 0.0)
    resumed["advantage_gap"] = resumed.get("advantage", 0.0) - control.get("advantage", 0.0)
    resumed["control_terminal_value"] = control.get("terminal_value")
    resumed["control_animal_loss"] = control.get("animal_loss")
    return resumed


def _stats(rows):
    valid = [r for r in rows if not r.get("runtime_error") and r.get("own_money") is not None]
    gaps = [float(r.get("own_money_gap", 0.0)) for r in valid]
    return {
        "conditions": len(valid), "runtime_failures": sum(bool(r.get("runtime_error")) for r in rows),
        "semantic_failures": sum(len(r.get("semantic_failures", [])) for r in rows),
        "animal_loss_games": sum(bool(r.get("animal_loss")) for r in valid),
        "mean_own_money": statistics.fmean(r["own_money"] for r in valid) if valid else None,
        "mean_control_money": statistics.fmean(r["control_own_money"] for r in valid) if valid else None,
        "mean_own_money_gap": statistics.fmean(gaps) if gaps else None,
        "median_own_money_gap": statistics.median(gaps) if gaps else None,
        "p10_own_money_gap": _percentile(gaps, .10), "p5_own_money_gap": _percentile(gaps, .05),
        "mean_advantage_gap": statistics.fmean(float(r.get("advantage_gap", 0.0)) for r in valid) if valid else None,
        "mean_terminal_value": statistics.fmean(r.get("terminal_value", 0.0) for r in valid) if valid else None,
        "max_terminal_value": max((r.get("terminal_value", 0.0) for r in valid), default=None),
        "recovery_events": sum(int((r.get("telemetry") or {}).get("recovery_events", 0)) for r in valid),
        "task_failures": sum(int((r.get("telemetry") or {}).get("task_failures", 0)) for r in valid),
    }


def _percentile(values, q):
    values = sorted(float(v) for v in values)
    if not values:
        return None
    position = (len(values) - 1) * q
    low = int(position)
    high = min(len(values) - 1, low + 1)
    return values[low] + (values[high] - values[low]) * (position - low)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[51000, 51001])
    parser.add_argument("--checkpoints", nargs="+", type=int, default=[24, 72, 120, 168, 240, 360, 480, 600])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", default="experiments/checkpoint_executor_resume_results.json")
    parser.add_argument("--partial", default="experiments/checkpoint_executor_resume_results.partial.json")
    args = parser.parse_args()
    jobs = [(seed, seat, checkpoint) for checkpoint in args.checkpoints for seed in args.seeds for seat in (0, 1)]
    partial = (ROOT / args.partial).resolve()
    output = (ROOT / args.output).resolve()
    rows = []
    if partial.is_file():
        try:
            rows = json.loads(partial.read_text()).get("rows", [])
        except Exception:
            rows = []
    done = {(int(r.get("seed", -1)), int(r.get("seat", -1)), int(r.get("checkpoint", -1))) for r in rows}
    todo = [job for job in jobs if job not in done]
    print(f"Running {len(todo)} resume conditions ({len(rows)} cached)", flush=True)
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = [pool.submit(_job, job) for job in todo]
        for i, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if i % 8 == 0 or i == len(futures):
                partial.parent.mkdir(parents=True, exist_ok=True)
                partial.write_text(json.dumps({"schema_version": 1, "rows": rows}, indent=2, sort_keys=True) + "\n")
                print(f"{i}/{len(futures)} complete", flush=True)
    rows.sort(key=lambda r: (int(r.get("checkpoint", -1)), int(r.get("seed", -1)), int(r.get("seat", -1))))
    by_checkpoint = {str(cp): _stats([r for r in rows if int(r.get("checkpoint", -1)) == cp]) for cp in args.checkpoints}
    payload = {
        "schema_version": 1,
        "design": "CurrentBest control versus commitment-first executor takeover at real checkpoints; no state editing",
        "seeds": [int(s) for s in args.seeds], "checkpoints": [int(c) for c in args.checkpoints],
        "baseline": BASELINE_PATH, "executor": EXECUTOR_PATH, "rows": rows,
        "by_checkpoint": by_checkpoint, "overall": _stats(rows),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    for checkpoint, summary in by_checkpoint.items():
        print(checkpoint, summary, flush=True)


if __name__ == "__main__":
    main()
