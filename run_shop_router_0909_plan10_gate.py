"""Reproduce Plan-10 failure and screen four one-primitive hardening patches."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import time

from kaggle_environments import make

from analyze_top_player_replays import _transition_ledger
from run_epic_experiments import _independent_shop_schedule, _run_with_fixed_shops
from run_raw55899537_final_validation import animal_escapes, economic_summary, semantic_validate, terminal_value


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "experiments/shop_router_0909_plan10_gate_raw.json"
OPPONENT = ROOT / "agents/top50_distilled/top50_observable_portfolio.py"
VARIANTS = {
    "exact": ROOT / "agents/shop_router_0909/main.py",
    "fix_a_reserve_sale": ROOT / "agents/shop_router_0909_hardened/v1_fix_a_reserve_sale.py",
    "fix_b_buy_one": ROOT / "agents/shop_router_0909_hardened/v1_fix_b_buy_one.py",
    "fix_c_reallocate_day14": ROOT / "agents/shop_router_0909_hardened/v1_fix_c_reallocate_day14.py",
    "fix_d_reallocate_day15": ROOT / "agents/shop_router_0909_hardened/v1_fix_d_reallocate_day15.py",
}
SEED = 1309401


def load_agent(path, tag):
    spec = importlib.util.spec_from_file_location(f"plan10_{tag}_{time.time_ns()}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module.agent


def total_wheat(obs, seat):
    private = obs["private"]
    return int(private["shed"].get("WHEAT", 0)) + sum(
        int(inv.get("WHEAT", 0)) for inv in private["inventories"]
    )


def animal_snapshot(obs, seat):
    farm = obs["farms"][seat]
    animals = []
    for y, row in enumerate(farm["tiles"]):
        for x, tile in enumerate(row):
            if isinstance(tile, dict) and tile.get("animal"):
                animals.append({
                    "position": [x, y], "animal": tile["animal"],
                    "placed_day": tile["placed_day"], "yield_units": tile["yield_units"],
                    "fed_today": tile["fed_today"],
                    "consecutive_unfed": tile["consecutive_unfed"],
                    "cared_today": tile["cared_today"],
                    "fertilizer_available": tile["fertilizer_available"],
                    "pending_care_bonus": tile["pending_care_bonus"],
                })
    return animals


def compact_snapshot(obs, action, seat):
    farm = obs["farms"][seat]
    positions = [farm["farmer"], *farm["hands"]]
    inventories = obs["private"]["inventories"]
    workers = [action.get("farmer", ["PASS"]), *action.get("hands", [])]
    worker_rows = []
    for index, position in enumerate(positions):
        issued = workers[index] if index < len(workers) else None
        tile = farm["tiles"][position[1]][position[0]]
        if issued and issued[0] in {"PICKUP", "FEED", "CARE", "COLLECT_FERTILIZER", "HARVEST", "DROP", "PLACE"}:
            worker_rows.append({
                "worker": index, "position": list(position), "action": issued,
                "inventory": inventories[index] if index < len(inventories) else {},
                "tile_kind": tile.get("kind") if isinstance(tile, dict) else tile,
                "tile_animal": tile.get("animal") if isinstance(tile, dict) else None,
            })
    return {
        "step": int(obs["step"]), "day": int(obs["day"]), "hour": int(obs["hour"]),
        "money": float(farm["money"]), "farmer": farm["farmer"], "hands": farm["hands"],
        "shed": obs["private"]["shed"], "inventories": inventories,
        "shed_wheat": int(obs["private"]["shed"].get("WHEAT", 0)),
        "total_held_wheat": total_wheat(obs, seat),
        "sheep_count": sum(a["animal"] == "SHEEP" for a in animal_snapshot(obs, seat)),
        "animal_count": len(animal_snapshot(obs, seat)),
        "animals": animal_snapshot(obs, seat),
        "shops": list(obs["town"]["unlocked_shops"]),
        "market_wheat": {
            "inventory": int(obs["market"]["inventory"]["WHEAT"]),
            "price": int(obs["market"]["prices"]["WHEAT"]),
        },
        "planned_action": deepcopy(json.loads((ROOT / "agents/shop_router_0909/actions.json").read_text())[10][int(obs["step"])]),
        "issued_action": deepcopy(action),
        "relevant_workers": worker_rows,
    }


def run_job(job):
    variant, path, seat = job
    module, candidate = load_agent(path, f"{variant}_{seat}")
    _, opponent = load_agent(OPPONENT, f"opponent_{variant}_{seat}")
    trace = []
    actions = []
    warnings = []

    def checked(obs):
        action = candidate(obs)
        actions.append(deepcopy(action))
        if 288 <= int(obs["step"]) <= 408:
            trace.append(compact_snapshot(deepcopy(obs), action, seat))
        try:
            semantic_validate(obs, action)
        except Exception as exc:
            warnings.append({"step": int(obs["step"]), "class": repr(exc)})
        return action

    pair = [opponent, opponent]
    pair[seat] = checked
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": SEED}, debug=False)
    _run_with_fixed_shops(env, pair, _independent_shop_schedule(SEED))
    replay = env.toJSON()
    ledgers = {}
    for index in range(1, len(replay["steps"])):
        previous = replay["steps"][index - 1]
        current = replay["steps"][index]
        step = int(previous[0]["observation"]["step"])
        if 288 <= step <= 408:
            values, mismatches = _transition_ledger(previous, current, replay["configuration"])
            ledger = values[seat]
            ledgers[step] = {
                "feed_successes": int(ledger["feed_actions"]),
                "harvest": dict(ledger["harvest_quantity"]),
                "market_buys": dict(ledger["product_quantity"]),
                "market_buy_spend": dict(ledger["product_spend"]),
                "sales": dict(ledger["sale_quantity"]),
                "sale_revenue": dict(ledger["sale_revenue"]),
                "reconciliation_mismatches": mismatches,
            }
    for row in trace:
        row["transition_ledger"] = ledgers.get(row["step"], {})
    final = env.steps[-1]
    economics = economic_summary(replay, seat)
    economics.pop("daily", None)
    plan = None
    if variant == "exact":
        plan = module._POLICY.players[seat].plan
    else:
        plan = candidate.exact_module._POLICY.players[seat].plan
    return {
        "variant": variant, "seed": SEED, "seat": seat, "shop_mode": "fixed",
        "shops_at_144": trace[0]["shops"][:2] if trace else None, "final_plan": plan,
        "steps": len(env.steps), "calls": len(actions),
        "own_money": float(final[seat].reward),
        "opponent_money": float(final[1 - seat].reward),
        "advantage": float(final[seat].reward) - float(final[1 - seat].reward),
        "livestock_escapes": animal_escapes(env.steps, seat),
        "terminal": terminal_value(final, seat),
        "strict_warning_count": len(warnings),
        "strict_warning_classes": sorted({row["class"] for row in warnings}),
        "action_hash": hashlib.sha256(json.dumps(actions, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "economics": economics,
        "trace": trace,
    }


def main():
    jobs = [(name, str(path), seat) for name, path in VARIANTS.items() for seat in (0, 1)]
    rows = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_job, job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: (row["variant"], row["seat"]))
    payload = {
        "design": "Known deterministic fixed-shop failure; exact and four one-primitive Plan-10 patches; both seats.",
        "seed": SEED,
        "rows": rows,
    }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    for row in rows:
        print(row["variant"], row["seat"], row["own_money"], row["advantage"], len(row["livestock_escapes"]))


if __name__ == "__main__":
    main()
