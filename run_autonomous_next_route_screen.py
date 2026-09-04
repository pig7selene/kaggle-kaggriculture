"""Cheap complete-route oracle screen for the autonomous next research stage.

This script never splices route actions.  Every candidate is a complete route
executed from turn 0, and every condition is paired by seed/opponent/seat with
the frozen observable portfolio.  The screen is intentionally small: it is a
falsification test before building a checkpoint-resumable executor.
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
DEFAULT_OUTPUT = ROOT / "experiments/autonomous_next_route_screen.json"
DEFAULT_PARTIAL = ROOT / "experiments/autonomous_next_route_screen.partial.json"

UNIT_OPS = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "PLANT", "WATER",
    "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP", "BUILD_PASTURE",
    "PICKUP", "DROP", "PLACE", "FEED", "CARE", "COLLECT_FERTILIZER",
}
MARKET_OPS = {"HIRE", "BUY_LAND", "BUY_SEED", "BUY_PRODUCT", "BUY_ANIMAL", "SELL"}
SELLABLE = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")

CANDIDATES = {
    "current_best": "agents/top50_distilled/top50_observable_portfolio.py",
    "family01_medoid": "agents/top50_distilled/raw/super_family_01_medoid.py",
    "family02_medoid": "agents/top50_distilled/raw/super_family_02_medoid.py",
    "family03_medoid": "agents/top50_distilled/raw/super_family_03_medoid.py",
    "family04_medoid": "agents/top50_distilled/raw/super_family_04_medoid.py",
    "family05_medoid": "agents/top50_distilled/raw/super_family_05_medoid.py",
    "raw_55899537": "agents/autonomous_next/top50_raw_55899537.py",
    "raw_55884271": "agents/autonomous_next/top50_raw_55884271.py",
}

OPPONENTS = {
    "current_best": "agents/top50_distilled/top50_observable_portfolio.py",
    "tetsuya": "agents/top3_tuned/raw_rank1_tetsuya.py",
    "crop_dusta": "agents/top3_tuned/raw_rank2_crop_dusta.py",
    "oceanmix": "agents/top3_tuned/raw_rank3_oceanmix.py",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: str):
    absolute = (ROOT / path).resolve()
    module_name = "autonext_screen_" + hashlib.sha256(str(absolute).encode()).hexdigest()[:16]
    spec = importlib.util.spec_from_file_location(module_name, absolute)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {absolute}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def _semantic_validate(obs, action):
    if not isinstance(action, dict) or set(action) != {"farmer", "hands", "market"}:
        raise AssertionError("action must contain farmer/hands/market only")
    farmer = action["farmer"]
    if not isinstance(farmer, list) or not farmer or farmer[0] not in UNIT_OPS:
        raise AssertionError("invalid farmer operation")
    expected_hands = len(obs["farms"][obs["player"]].get("hands", []))
    hands = action["hands"]
    if not isinstance(hands, list) or len(hands) != expected_hands:
        raise AssertionError(f"expected {expected_hands} hand actions, got {len(hands) if isinstance(hands, list) else 'non-list'}")
    for request in hands:
        if not isinstance(request, list) or not request or request[0] not in UNIT_OPS:
            raise AssertionError("invalid hand operation")
    market = action["market"]
    if not isinstance(market, list) or len(market) > 10:
        raise AssertionError("invalid market queue")
    for order in market:
        if not isinstance(order, list) or not order or order[0] not in MARKET_OPS:
            raise AssertionError("invalid market operation")
        if order[0] in {"HIRE", "BUY_LAND"}:
            if len(order) != 1:
                raise AssertionError("wrong zero-argument market order")
        elif len(order) != 3 or not isinstance(order[2], int) or order[2] <= 0:
            raise AssertionError("wrong quantity market order")


def _animal_count(observation, seat):
    farm = observation["farms"][seat]
    count = 0
    for row in farm.get("tiles", []):
        for tile in row:
            if isinstance(tile, dict) and tile.get("animal"):
                count += 1
    private = observation.get("private", {})
    count += sum(int(private.get("shed", {}).get(a, 0)) for a in ("GOOSE", "COW", "SHEEP"))
    count += sum(sum(int(inv.get(a, 0)) for inv in private.get("inventories", [])) for a in ("GOOSE", "COW", "SHEEP"))
    return count


def _terminal_value(final_state, seat):
    observation = final_state[seat].observation
    private = observation.get("private", {})
    prices = observation.get("market", {}).get("prices", {})
    quantities = defaultdict(int)
    for item in SELLABLE:
        quantities[item] += int(private.get("shed", {}).get(item, 0))
        quantities[item] += sum(int(inv.get(item, 0)) for inv in private.get("inventories", []))
    value = sum(quantities[item] * float(prices.get(item, 1)) for item in SELLABLE)
    farm = observation["farms"][seat]
    field = defaultdict(int)
    for row in farm.get("tiles", []):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT" and int(tile.get("yield_units", 0)) > 0:
                field[tile.get("crop")] += int(tile.get("yield_units", 0))
            elif tile.get("animal") and int(tile.get("yield_units", 0)) > 0:
                product = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}.get(tile.get("animal"))
                if product:
                    field[product] += int(tile.get("yield_units", 0))
    for item, quantity in field.items():
        value += quantity * float(prices.get(item, 1))
    return {"value": float(value), "shed": dict(sorted((k, v) for k, v in quantities.items() if v)), "field": dict(sorted(field.items()))}


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
            _semantic_validate(obs, action)
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
    own = final[int(seat)]
    rival = final[1 - int(seat)]
    counts = [_animal_count(state[int(seat)].observation, int(seat)) for state in env.steps]
    return {
        "candidate": candidate_name, "opponent": opponent_name, "seed": int(seed), "seat": int(seat),
        "runtime_error": None, "semantic_failures": semantic_failures, "calls": calls,
        "own_money": float(own.reward), "opponent_money": float(rival.reward),
        "advantage": float(own.reward) - float(rival.reward),
        "animal_count_max": max(counts), "animal_count_final": counts[-1],
        "livestock_loss": counts[-1] < max(counts),
        "terminal": _terminal_value(final, int(seat)),
        "telemetry": {
            "route_requests": int(getattr(candidate, "telemetry", {}).get("all_route_requests", 0)),
            "route_matches": int(getattr(candidate, "telemetry", {}).get("all_route_matches", 0)),
            "repairs": int(sum((getattr(candidate, "telemetry", {}).get("repairs", {}) or {}).values())),
            "repair_abort": int(getattr(candidate, "telemetry", {}).get("repair_abort", 0)),
            "fallback": int((getattr(candidate, "telemetry", {}).get("mode_steps", {}) or {}).get("FALLBACK", 0)),
        },
    }


def _percentile(values, fraction):
    values = sorted(float(x) for x in values)
    if not values:
        return None
    point = (len(values) - 1) * float(fraction)
    low = int(point)
    high = min(len(values) - 1, low + 1)
    return values[low] + (values[high] - values[low]) * (point - low)


def _stats(rows):
    valid = [r for r in rows if not r.get("runtime_error") and r.get("own_money") is not None]
    if not valid:
        return {"games": 0, "runtime_failures": len(rows), "semantic_failures": sum(len(r.get("semantic_failures", [])) for r in rows)}
    adv = [r["advantage"] for r in valid]
    return {
        "games": len(valid),
        "wins": sum(x > 0 for x in adv), "losses": sum(x < 0 for x in adv), "ties": sum(x == 0 for x in adv),
        "win_rate": sum(x > 0 for x in adv) / len(valid),
        "average_money": statistics.fmean(r["own_money"] for r in valid),
        "average_opponent_money": statistics.fmean(r["opponent_money"] for r in valid),
        "average_advantage": statistics.fmean(adv), "median_advantage": statistics.median(adv),
        "p10_advantage": _percentile(adv, .10), "p5_advantage": _percentile(adv, .05),
        "worst_advantage": min(adv), "variance_advantage": statistics.pvariance(adv) if len(adv) > 1 else 0.0,
        "livestock_loss_games": sum(bool(r.get("livestock_loss")) for r in valid),
        "mean_terminal_value": statistics.fmean(r.get("terminal", {}).get("value", 0.0) for r in valid),
        "runtime_failures": sum(bool(r.get("runtime_error")) for r in rows),
        "semantic_failures": sum(len(r.get("semantic_failures", [])) for r in rows),
        "route_realization": sum(r.get("telemetry", {}).get("route_matches", 0) for r in valid) / max(1, sum(r.get("telemetry", {}).get("route_requests", 0) for r in valid)),
    }


def _paired_stats(rows, baseline_name="current_best"):
    grouped = defaultdict(dict)
    for row in rows:
        grouped[(row["opponent"], int(row["seed"]), int(row["seat"]))][row["candidate"]] = row
    output = {}
    for candidate in sorted({r["candidate"] for r in rows}):
        if candidate == baseline_name:
            continue
        pairs = []
        for values in grouped.values():
            if candidate not in values or baseline_name not in values:
                continue
            c, b = values[candidate], values[baseline_name]
            if c.get("own_money") is None or b.get("own_money") is None:
                continue
            pairs.append({
                "own_delta": c["own_money"] - b["own_money"],
                "advantage_delta": c["advantage"] - b["advantage"],
                "candidate_advantage": c["advantage"], "baseline_advantage": b["advantage"],
                "opponent": c["opponent"], "seed": c["seed"], "seat": c["seat"],
            })
        own = [p["own_delta"] for p in pairs]
        ad = [p["advantage_delta"] for p in pairs]
        by_opp = {}
        for opponent in sorted({p["opponent"] for p in pairs}):
            subset = [p for p in pairs if p["opponent"] == opponent]
            vals = [p["own_delta"] for p in subset]
            av = [p["advantage_delta"] for p in subset]
            by_opp[opponent] = {
                "games": len(subset), "mean_own_delta": statistics.fmean(vals), "median_own_delta": statistics.median(vals),
                "p10_own_delta": _percentile(vals, .10), "mean_advantage_delta": statistics.fmean(av),
                "candidate_wins": sum(p["candidate_advantage"] > 0 for p in subset),
                "candidate_losses": sum(p["candidate_advantage"] < 0 for p in subset),
            }
        output[candidate] = {
            "games": len(pairs), "mean_own_delta": statistics.fmean(own) if own else None,
            "median_own_delta": statistics.median(own) if own else None,
            "p10_own_delta": _percentile(own, .10), "p5_own_delta": _percentile(own, .05),
            "worst_own_delta": min(own) if own else None,
            "mean_advantage_delta": statistics.fmean(ad) if ad else None,
            "median_advantage_delta": statistics.median(ad) if ad else None,
            "p10_advantage_delta": _percentile(ad, .10), "negative_own_rate": sum(x < 0 for x in own) / len(own) if own else None,
            "by_opponent": by_opp,
        }
    return output


def _jobs(candidate_names, opponent_names, seeds):
    jobs = []
    for candidate_name in candidate_names:
        for opponent_name in opponent_names:
            for seed in seeds:
                for seat in (0, 1):
                    jobs.append((candidate_name, CANDIDATES[candidate_name], opponent_name, OPPONENTS[opponent_name], int(seed), seat))
    return jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[50600, 50601])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--candidates", default=",")
    parser.add_argument("--opponents", default="current_best,tetsuya,crop_dusta,oceanmix")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--partial", default=str(DEFAULT_PARTIAL))
    args = parser.parse_args()
    candidate_names = [x for x in (args.candidates.split(",") if args.candidates else CANDIDATES) if x in CANDIDATES]
    if not candidate_names:
        candidate_names = list(CANDIDATES)
    opponent_names = [x for x in args.opponents.split(",") if x in OPPONENTS]
    if not opponent_names:
        opponent_names = list(OPPONENTS)
    jobs = _jobs(candidate_names, opponent_names, args.seeds)
    partial_path = Path(args.partial).resolve()
    output_path = Path(args.output).resolve()
    rows = []
    if partial_path.is_file():
        try:
            rows = json.loads(partial_path.read_text()).get("rows", [])
        except Exception:
            rows = []
    done = {(r.get("candidate"), r.get("opponent"), int(r.get("seed", -1)), int(r.get("seat", -1))) for r in rows}
    todo = [j for j in jobs if (j[0], j[2], j[4], j[5]) not in done]
    print(f"Running {len(todo)} new route-screen games ({len(rows)} cached)", flush=True)
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = [pool.submit(_run_game, job) for job in todo]
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 16 == 0 or index == len(futures):
                partial_path.write_text(json.dumps({"schema_version": 1, "rows": rows}, indent=2, sort_keys=True) + "\n")
                print(f"{index}/{len(futures)} complete", flush=True)
    rows.sort(key=lambda r: (r.get("candidate", ""), r.get("opponent", ""), r.get("seed", 0), r.get("seat", 0)))
    summaries = {name: _stats([r for r in rows if r.get("candidate") == name]) for name in candidate_names}
    paired = _paired_stats(rows)
    payload = {
        "schema_version": 1,
        "design": "complete-route medoid oracle screen; natural fixed seeds; both seats; paired own money against frozen observable portfolio",
        "seeds": [int(x) for x in args.seeds], "candidates": {k: CANDIDATES[k] for k in candidate_names},
        "opponents": {k: OPPONENTS[k] for k in opponent_names}, "candidate_hashes": {k: _sha(ROOT / CANDIDATES[k]) for k in candidate_names},
        "baseline": "current_best", "games": len(rows), "rows": rows, "summaries": summaries, "paired_vs_current_best": paired,
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output_path)
    for name in sorted(paired, key=lambda n: paired[n]["mean_own_delta"] if paired[n]["mean_own_delta"] is not None else -1e99, reverse=True):
        p = paired[name]; s = summaries[name]
        print(name, "pairs", p["games"], "own", round(p["mean_own_delta"], 1), "adv", round(p["mean_advantage_delta"], 1), "p10", round(p["p10_own_delta"], 1), "H2H", f"{s.get('wins', 0)}/{s.get('losses', 0)}/{s.get('ties', 0)}", "escapes", s.get("livestock_loss_games"), "route", round(s.get("route_realization", 0), 6), flush=True)


if __name__ == "__main__":
    main()
