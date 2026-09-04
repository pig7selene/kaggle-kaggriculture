"""Attribute the passive checkpoint-executor continuation gap.

Each row compares a fresh CurrentBest continuation with a fresh takeover by
the state-based executor from the identical checkpoint/seed/seat.  Accounting
is action-derived (market order quantities and observed prices) and is used to
choose the next capability, not as a replacement for the simulator's bank.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import json
from pathlib import Path
import statistics

from kaggle_environments import make

from run_checkpoint_executor_resume import BASELINE_PATH, EXECUTOR_PATH, _load, _validate


ROOT = Path(__file__).resolve().parent
CROP_PRODUCTS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}
ANIMAL_PRODUCTS = {"EGG", "MILK", "WOOL"}
FIB = (1, 1, 2, 3, 5, 8, 13, 21, 34)
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
ANIMAL_COST = {"GOOSE": 300, "COW": 400, "SHEEP": 500}
LAND_COST = (1000, 2000, 4000)


def _counts(obs, seat):
    farm = obs["farms"][seat]
    plants = {}
    animals = {}
    for y, row in enumerate(farm.get("tiles", [])):
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get("kind") == "PLANT":
                plants[tile.get("crop", "?")] = plants.get(tile.get("crop", "?"), 0) + 1
            if isinstance(tile, dict) and tile.get("animal"):
                animals[tile.get("animal", "?")] = animals.get(tile.get("animal", "?"), 0) + 1
    return plants, animals


def _action_metrics(obs, action, seat):
    prices = obs.get("market", {}).get("prices", {})
    farm = obs["farms"][seat]
    out = {
        "sell_revenue": 0.0, "crop_sell_revenue": 0.0,
        "animal_sell_revenue": 0.0, "fertilizer_sell_revenue": 0.0,
        "buy_product_spend": 0.0, "seed_spend": 0.0,
        "animal_purchase_spend": 0.0, "land_spend": 0.0,
        "hire_spend": 0.0, "market_sell_units": {},
        "market_buy_units": {}, "hire_count": 0,
    }
    for order in action.get("market", []) if isinstance(action, dict) else []:
        if not order:
            continue
        op = order[0]
        if op == "SELL" and len(order) >= 3:
            item, qty = order[1], max(0, int(order[2]))
            revenue = qty * float(prices.get(item, 1))
            out["sell_revenue"] += revenue
            out["market_sell_units"][item] = out["market_sell_units"].get(item, 0) + qty
            if item in CROP_PRODUCTS:
                out["crop_sell_revenue"] += revenue
            elif item in ANIMAL_PRODUCTS:
                out["animal_sell_revenue"] += revenue
            elif item == "FERTILIZER":
                out["fertilizer_sell_revenue"] += revenue
        elif op == "BUY_PRODUCT" and len(order) >= 3:
            item, qty = order[1], max(0, int(order[2]))
            out["buy_product_spend"] += qty * float(prices.get(item, 1))
            out["market_buy_units"][item] = out["market_buy_units"].get(item, 0) + qty
        elif op == "BUY_SEED" and len(order) >= 3:
            item, qty = order[1], max(0, int(order[2]))
            out["seed_spend"] += qty * SEED_COST.get(item, 0)
        elif op == "BUY_ANIMAL" and len(order) >= 3:
            item, qty = order[1], max(0, int(order[2]))
            out["animal_purchase_spend"] += qty * ANIMAL_COST.get(item, 0)
        elif op == "BUY_LAND":
            owned = len(farm.get("unlocked_quadrants", []))
            out["land_spend"] += LAND_COST[min(max(0, owned - 1), len(LAND_COST) - 1)]
        elif op == "HIRE":
            index = int(farm.get("hires_today", 0)) + out["hire_count"]
            out["hire_spend"] += FIB[min(index, len(FIB) - 1)]
            out["hire_count"] += 1
    return out


def _run_variant(path, opponent_path, seed, seat, checkpoint):
    agent = _load(path, f"gap_agent_{path}_{seed}_{seat}_{checkpoint}")
    # Every variant follows the same real CurrentBest trajectory up to the
    # checkpoint.  The executor is only called after takeover; otherwise a
    # passive executor run from step 0 would measure the wrong experiment.
    opener = _load(BASELINE_PATH, f"gap_opener_{path}_{seed}_{seat}_{checkpoint}")
    opponent = _load(opponent_path, f"gap_opp_{path}_{seed}_{seat}_{checkpoint}")
    semantic = []
    metrics = {k: 0.0 for k in ("sell_revenue", "crop_sell_revenue", "animal_sell_revenue", "fertilizer_sell_revenue", "buy_product_spend", "seed_spend", "animal_purchase_spend", "land_spend", "hire_spend", "hire_count")}
    sell_units = {}
    plants_series = []
    animals_series = []
    idle_units = 0
    total_units = 0

    def controlled(obs):
        nonlocal idle_units, total_units
        step = int(obs.get("step", 0))
        action = opener(obs) if step < checkpoint else agent(obs)
        try:
            _validate(obs, action)
        except Exception as exc:
            semantic.append({"step": int(obs.get("step", -1)), "error": repr(exc)})
        if step >= checkpoint:
            stepm = _action_metrics(obs, action, seat)
            for key in metrics:
                metrics[key] += stepm[key]
            for item, qty in stepm["market_sell_units"].items():
                sell_units[item] = sell_units.get(item, 0) + qty
            units = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
            total_units += len(units)
            idle_units += sum(1 for value in units if value and value[0] == "PASS")
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
        return {"runtime_error": runtime or f"steps={len(getattr(env, 'steps', []))}", "semantic_failures": semantic}
    for i in range(checkpoint, 720, 24):
        obs = env.steps[i][seat].observation
        p, a = _counts(obs, seat)
        plants_series.append({"day": int(obs.get("day", i // 24)), "total": sum(p.values()), "by_crop": p})
        animals_series.append({"day": int(obs.get("day", i // 24)), "total": sum(a.values()), "by_animal": a})
    final_obs = env.steps[-1][seat].observation
    fp, fa = _counts(final_obs, seat)
    metrics["idle_unit_rate"] = idle_units / total_units if total_units else 0.0
    metrics["final_money"] = float(env.steps[-1][seat].reward)
    metrics["final_plants"] = sum(fp.values())
    metrics["final_animals"] = sum(fa.values())
    return {
        "runtime_error": None, "semantic_failures": semantic,
        "metrics": metrics, "sell_units": sell_units,
        "plants_series": plants_series, "animals_series": animals_series,
    }


def _job(job):
    seed, seat, checkpoint = job
    control = _run_variant(BASELINE_PATH, BASELINE_PATH, seed, seat, checkpoint)
    resumed = _run_variant(EXECUTOR_PATH, BASELINE_PATH, seed, seat, checkpoint)
    if control.get("runtime_error") or resumed.get("runtime_error"):
        return {"seed": seed, "seat": seat, "checkpoint": checkpoint, "control": control, "executor": resumed}
    cm, em = control["metrics"], resumed["metrics"]
    delta = {key: float(em.get(key, 0.0)) - float(cm.get(key, 0.0)) for key in em if isinstance(em.get(key), (int, float))}
    delta["money_gap"] = float(em["final_money"]) - float(cm["final_money"])
    delta["crop_revenue_gap"] = em["crop_sell_revenue"] - cm["crop_sell_revenue"]
    delta["animal_revenue_gap"] = em["animal_sell_revenue"] - cm["animal_sell_revenue"]
    delta["fertilizer_revenue_gap"] = em["fertilizer_sell_revenue"] - cm["fertilizer_sell_revenue"]
    return {"seed": seed, "seat": seat, "checkpoint": checkpoint,
            "control": control, "executor": resumed, "delta": delta}


def _sum_delta(rows, key):
    values = [float(r.get("delta", {}).get(key, 0.0)) for r in rows if r.get("delta")]
    return statistics.fmean(values) if values else 0.0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=[54000, 54001])
    parser.add_argument("--checkpoints", nargs="+", type=int, default=[24, 72, 120, 168, 240, 360, 480, 600])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", default="experiments/checkpoint_executor_gap_attribution.json")
    args = parser.parse_args()
    jobs = [(seed, seat, checkpoint) for checkpoint in args.checkpoints for seed in args.seeds for seat in (0, 1)]
    rows = []
    with ProcessPoolExecutor(max_workers=max(1, int(args.workers))) as pool:
        futures = [pool.submit(_job, job) for job in jobs]
        for i, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if i % 8 == 0 or i == len(futures):
                print(f"{i}/{len(futures)} complete", flush=True)
    valid = [r for r in rows if r.get("delta")]
    aggregate = {
        "conditions": len(valid),
        "mean_final_money_gap": _sum_delta(rows, "money_gap"),
        "mean_crop_revenue_gap": _sum_delta(rows, "crop_revenue_gap"),
        "mean_animal_revenue_gap": _sum_delta(rows, "animal_revenue_gap"),
        "mean_fertilizer_revenue_gap": _sum_delta(rows, "fertilizer_revenue_gap"),
        "mean_seed_spend_gap": _sum_delta(rows, "seed_spend"),
        "mean_animal_purchase_spend_gap": _sum_delta(rows, "animal_purchase_spend"),
        "mean_land_spend_gap": _sum_delta(rows, "land_spend"),
        "mean_hire_spend_gap": _sum_delta(rows, "hire_spend"),
        "mean_idle_unit_rate_gap": _sum_delta(rows, "idle_unit_rate"),
        "mean_final_plants_gap": _sum_delta(rows, "final_plants"),
        "mean_final_animals_gap": _sum_delta(rows, "final_animals"),
        "runtime_failures": sum(bool(r.get("control", {}).get("runtime_error") or r.get("executor", {}).get("runtime_error")) for r in rows),
        "semantic_failures": sum(len(r.get("control", {}).get("semantic_failures", [])) + len(r.get("executor", {}).get("semantic_failures", [])) for r in rows),
    }
    payload = {"schema_version": 1, "baseline": BASELINE_PATH, "executor": EXECUTOR_PATH,
               "seeds": [int(s) for s in args.seeds], "checkpoints": [int(c) for c in args.checkpoints],
               "rows": rows, "aggregate": aggregate}
    output = (ROOT / args.output).resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output); print(aggregate)


if __name__ == "__main__":
    main()
