"""Cheap paired benchmark for a market-only residual.

Both the frozen portfolio and the residual run from turn 0 on identical seeds,
opponents, and seats.  The residual may only permute SELL orders already
present in the frozen action for that same turn.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics

from kaggle_environments import make


ROOT = Path(__file__).resolve().parent
BASELINE = "agents/top50_distilled/top50_observable_portfolio.py"
CANDIDATES = {
    "current_best": BASELINE,
    "market_residual_reorder_v1": "agents/autonomous_next/market_residual_reorder_v1.py",
    "market_residual_horizon_v1": "agents/autonomous_next/market_residual_horizon_v1.py",
}
OPPONENTS = {
    "current_best": BASELINE,
    "tetsuya": "agents/top3_tuned/raw_rank1_tetsuya.py",
    "crop_dusta": "agents/top3_tuned/raw_rank2_crop_dusta.py",
    "oceanmix": "agents/top3_tuned/raw_rank3_oceanmix.py",
}
UNIT_OPS = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER", "HARVEST",
    "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE", "PICKUP", "DROP",
    "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER",
}
MARKET_OPS = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: str):
    absolute = (ROOT / path).resolve()
    module_name = "autonext_market_" + hashlib.sha256(str(absolute).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(module_name, absolute)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {absolute}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def _validate(obs, action):
    if not isinstance(action, dict) or set(action) != {"farmer", "hands", "market"}:
        raise AssertionError("action schema")
    if not isinstance(action["farmer"], list) or not action["farmer"] or action["farmer"][0] not in UNIT_OPS:
        raise AssertionError("farmer op")
    expected = len(obs["farms"][obs["player"]].get("hands", []))
    if not isinstance(action["hands"], list) or len(action["hands"]) != expected:
        raise AssertionError(f"hand count {len(action.get('hands', []))} != {expected}")
    for unit in action["hands"]:
        if not isinstance(unit, list) or not unit or unit[0] not in UNIT_OPS:
            raise AssertionError("hand op")
    if not isinstance(action["market"], list) or len(action["market"]) > 10:
        raise AssertionError("market queue")
    for order in action["market"]:
        if not isinstance(order, list) or not order or order[0] not in MARKET_OPS:
            raise AssertionError("market op")
        if order[0] in {"HIRE", "BUY_LAND"}:
            if len(order) != 1:
                raise AssertionError("market arity")
        elif len(order) != 3 or not isinstance(order[2], int) or order[2] <= 0:
            raise AssertionError("market quantity")


def _run_game(job):
    candidate_name, candidate_path, opponent_name, opponent_path, seed, seat = job
    candidate = _load(candidate_path)
    opponent = _load(opponent_path)
    semantic_failures = []
    calls = 0

    def checked(obs):
        nonlocal calls
        calls += 1
        action = candidate(obs)
        try:
            _validate(obs, action)
        except Exception as exc:
            semantic_failures.append({"step": int(obs.get("step", -1)), "error": repr(exc), "action": deepcopy(action)})
        return action

    pair = [opponent, opponent]
    pair[int(seat)] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    runtime_error = None
    try:
        env.run(pair)
    except Exception as exc:
        runtime_error = repr(exc)
    if runtime_error or len(getattr(env, "steps", [])) != 720:
        return {
            "candidate": candidate_name, "opponent": opponent_name, "seed": int(seed), "seat": int(seat),
            "runtime_error": runtime_error or f"steps={len(getattr(env, 'steps', []))}",
            "semantic_failures": semantic_failures, "calls": calls,
        }
    final = env.steps[-1]
    own = float(final[int(seat)].reward)
    rival = float(final[1 - int(seat)].reward)
    telemetry = getattr(candidate, "telemetry", {})
    return {
        "candidate": candidate_name, "opponent": opponent_name, "seed": int(seed), "seat": int(seat),
        "runtime_error": None, "semantic_failures": semantic_failures, "calls": calls,
        "own_money": own, "opponent_money": rival, "advantage": own - rival,
        "telemetry": {
            "reorder_calls": int(telemetry.get("reorder_calls", 0)),
            "reordered_turns": int(telemetry.get("reordered_turns", 0)),
            "assignments": int(telemetry.get("assignments", 0)),
            "restored": int(telemetry.get("restored", 0)),
            "optimizer_errors": int(telemetry.get("errors", 0)),
            "estimated_original_revenue": float(telemetry.get("estimated_original_revenue", 0.0)),
            "estimated_optimized_revenue": float(telemetry.get("estimated_optimized_revenue", 0.0)),
            "base_parent": telemetry.get("portfolio_parent"),
        },
    }


def _percentile(values, q):
    values = sorted(float(v) for v in values)
    if not values:
        return None
    pos = (len(values) - 1) * q
    lo = int(pos)
    hi = min(len(values) - 1, lo + 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def _stats(rows):
    valid = [r for r in rows if r.get("runtime_error") is None and r.get("own_money") is not None]
    adv = [r["advantage"] for r in valid]
    return {
        "games": len(valid),
        "wins": sum(v > 0 for v in adv), "losses": sum(v < 0 for v in adv), "ties": sum(v == 0 for v in adv),
        "win_rate": sum(v > 0 for v in adv) / len(adv) if adv else None,
        "average_money": statistics.fmean(r["own_money"] for r in valid) if valid else None,
        "average_opponent_money": statistics.fmean(r["opponent_money"] for r in valid) if valid else None,
        "average_advantage": statistics.fmean(adv) if adv else None,
        "median_advantage": statistics.median(adv) if adv else None,
        "p10_advantage": _percentile(adv, .10), "p5_advantage": _percentile(adv, .05),
        "variance_advantage": statistics.pvariance(adv) if len(adv) > 1 else 0.0,
        "runtime_failures": sum(bool(r.get("runtime_error")) for r in rows),
        "semantic_failures": sum(len(r.get("semantic_failures", [])) for r in rows),
        "reordered_turns": sum(r.get("telemetry", {}).get("reordered_turns", 0) for r in valid),
        "assignments": sum(r.get("telemetry", {}).get("assignments", 0) for r in valid),
        "optimizer_errors": sum(r.get("telemetry", {}).get("optimizer_errors", 0) for r in valid),
        "estimated_revenue_gain": sum(
            r.get("telemetry", {}).get("estimated_optimized_revenue", 0.0)
            - r.get("telemetry", {}).get("estimated_original_revenue", 0.0) for r in valid
        ),
    }


def _paired(rows):
    grouped = defaultdict(dict)
    for row in rows:
        grouped[(row["opponent"], int(row["seed"]), int(row["seat"]))][row["candidate"]] = row
    by_candidate = {}
    for candidate in CANDIDATES:
        if candidate == "current_best":
            continue
        pairs = []
        for values in grouped.values():
            if candidate not in values or "current_best" not in values:
                continue
            c, b = values[candidate], values["current_best"]
            if c.get("own_money") is None or b.get("own_money") is None:
                continue
            pairs.append({
                "opponent": c["opponent"], "seed": c["seed"], "seat": c["seat"],
                "own_delta": c["own_money"] - b["own_money"],
                "advantage_delta": c["advantage"] - b["advantage"],
                "candidate_advantage": c["advantage"],
            })
        own = [p["own_delta"] for p in pairs]
        adv = [p["advantage_delta"] for p in pairs]
        by_opp = {}
        for opp in sorted({p["opponent"] for p in pairs}):
            subset = [p for p in pairs if p["opponent"] == opp]
            vals = [p["own_delta"] for p in subset]
            by_opp[opp] = {
                "games": len(subset), "mean_own_delta": statistics.fmean(vals) if vals else None,
                "median_own_delta": statistics.median(vals) if vals else None,
                "p10_own_delta": _percentile(vals, .10),
                "mean_advantage_delta": statistics.fmean(p["advantage_delta"] for p in subset) if subset else None,
                "candidate_wins": sum(p["candidate_advantage"] > 0 for p in subset),
                "candidate_losses": sum(p["candidate_advantage"] < 0 for p in subset),
            }
        by_candidate[candidate] = {
            "games": len(pairs), "mean_own_delta": statistics.fmean(own) if own else None,
            "median_own_delta": statistics.median(own) if own else None,
            "p10_own_delta": _percentile(own, .10), "p5_own_delta": _percentile(own, .05),
            "mean_advantage_delta": statistics.fmean(adv) if adv else None,
            "median_advantage_delta": statistics.median(adv) if adv else None,
            "negative_own_rate": sum(v < 0 for v in own) / len(own) if own else None,
            "by_opponent": by_opp,
        }
    return by_candidate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(50800, 50808)))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--opponents", default="current_best,tetsuya,crop_dusta,oceanmix")
    parser.add_argument("--output", default="experiments/autonomous_market_residual.json")
    parser.add_argument("--partial", default="experiments/autonomous_market_residual.partial.json")
    args = parser.parse_args()
    opponents = [x for x in args.opponents.split(",") if x in OPPONENTS]
    jobs = []
    for candidate_name, candidate_path in CANDIDATES.items():
        for opponent_name in opponents:
            for seed in args.seeds:
                for seat in (0, 1):
                    jobs.append((candidate_name, candidate_path, opponent_name, OPPONENTS[opponent_name], int(seed), seat))
    partial = (ROOT / args.partial).resolve()
    output = (ROOT / args.output).resolve()
    rows = []
    if partial.is_file():
        try:
            rows = json.loads(partial.read_text()).get("rows", [])
        except Exception:
            rows = []
    done = {(r.get("candidate"), r.get("opponent"), int(r.get("seed", -1)), int(r.get("seat", -1))) for r in rows}
    todo = [j for j in jobs if (j[0], j[2], j[4], j[5]) not in done]
    print(f"Running {len(todo)} market-residual games ({len(rows)} cached)", flush=True)
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = [pool.submit(_run_game, job) for job in todo]
        for i, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if i % 16 == 0 or i == len(futures):
                partial.parent.mkdir(parents=True, exist_ok=True)
                partial.write_text(json.dumps({"schema_version": 1, "rows": rows}, indent=2, sort_keys=True) + "\n")
                print(f"{i}/{len(futures)} complete", flush=True)
    rows.sort(key=lambda r: (r.get("candidate", ""), r.get("opponent", ""), r.get("seed", 0), r.get("seat", 0)))
    summaries = {name: _stats([r for r in rows if r.get("candidate") == name]) for name in CANDIDATES}
    payload = {
        "schema_version": 1,
        "design": "paired market-only residual; existing SELL slots permuted within a turn; all other route actions frozen",
        "seeds": [int(x) for x in args.seeds], "candidates": {k: CANDIDATES[k] for k in CANDIDATES},
        "candidate_hashes": {k: _sha(ROOT / v) for k, v in CANDIDATES.items()},
        "opponents": {k: OPPONENTS[k] for k in opponents}, "rows": rows,
        "summaries": summaries, "paired_vs_current_best": _paired(rows),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    for name, summary in summaries.items():
        print(name, summary, flush=True)
    for name, result in _paired(rows).items():
        print("paired", name, result, flush=True)


if __name__ == "__main__":
    main()
