"""Read-only local-to-leaderboard transfer-gap experiments.

The frozen agent and submission artifacts are inputs only.  Results are written
incrementally under experiments/ so every stage is resumable.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time

from kaggle_environments import make

from mine_top50_strategies import _economic_timeline
from run_raw55899537_final_validation import economic_summary, farm_counts, terminal_value
from run_epic_experiments import _run_with_fixed_shops


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
TMP = Path("/private/tmp/lb_gap_opponents")
FROZEN = ROOT / "agents/shop_router_0909_hardened/main.py"
EXACT = ROOT / "agents/shop_router_0909/main.py"
CURRENT = ROOT / "agents/top50_distilled/top50_observable_portfolio.py"
V2 = ROOT / "agents/super_replay_v2/super_backbone_v2.py"

CANDIDATES = {
    "hardened": FROZEN,
    "exact": EXACT,
    "previous_current_best": CURRENT,
    "v2": V2,
    "terminal_e182": TMP / "most_powerfull/main.py",
    "terminal_r31": TMP / "market_smart/main.py",
}
OPPONENTS = {
    "shape_shop_current": TMP / "shape_shop_current/main.py",
    "farming_v3_current": TMP / "farming_v3_current/main.py",
    "market_smart_terminal": TMP / "market_smart/main.py",
    "most_powerfull_terminal": TMP / "most_powerfull/main.py",
    "previous_current_best": CURRENT,
    "v2": V2,
    "hardened_mirror": FROZEN,
    "exact_mirror": EXACT,
}
CURRENT_META = (
    "shape_shop_current",
    "farming_v3_current",
    "market_smart_terminal",
    "most_powerfull_terminal",
)
CONTROLS = ("previous_current_best", "v2")
PRODUCTS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
ANIMAL_PRODUCT = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}

PHASE_A_SEEDS = (2609100,)
PHASE_B_SEEDS = (2609101, 2609102, 2609103, 2609104)
CONTROL_SEEDS = (2609100, 2609101)
ORACLE_SEEDS = (2609100,)
PIZZA_SEEDS = (2609110,)

PARTIALS = {
    "phase_a": EXP / "lb_gap_phase_a.partial.json",
    "phase_b": EXP / "lb_gap_phase_b.partial.json",
    "controls": EXP / "lb_gap_controls.partial.json",
    "terminal": EXP / "lb_gap_terminal_counterfactual.partial.json",
    "mirrors": EXP / "lb_gap_mirrors.partial.json",
    "oracle": EXP / "lb_gap_oracle.partial.json",
    "pizza": EXP / "lb_gap_pizza_yarn.partial.json",
    "phase_a_1327": EXP / "lb_gap_phase_a_1327.partial.json",
    "phase_b_1327": EXP / "lb_gap_phase_b_1327.partial.json",
    "controls_1327": EXP / "lb_gap_controls_1327.partial.json",
    "terminal_1327": EXP / "lb_gap_terminal_counterfactual_1327.partial.json",
    "mirrors_1327": EXP / "lb_gap_mirrors_1327.partial.json",
    "oracle_1327": EXP / "lb_gap_oracle_1327.partial.json",
    "pizza_1327": EXP / "lb_gap_pizza_yarn_1327.partial.json",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_agent(path: Path, tag: str):
    name = f"lb_gap_{tag}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module, module.agent


def selected_plan(module, agent, player: int):
    if hasattr(agent, "exact_module"):
        state = agent.exact_module._POLICY.players.get(player)
        return None if state is None else int(state.plan)
    policy = getattr(module, "_POLICY", None)
    if policy is not None:
        state = getattr(policy, "players", {}).get(player)
        return None if state is None else int(state.plan)
    return None


def forced_hardened(module, plan: int):
    exact = module.agent.exact_module
    policy = exact.Policy(ROOT / "agents/shop_router_0909")

    def agent(observation, configuration=None):
        step = int(observation["step"])
        player = int(observation["player"])
        state = policy.players.get(player)
        if state is None or step <= state.last_step:
            state = policy.players[player] = exact.DayState()
        state.last_step = step
        if step == exact.ROUTE_STEP:
            state.plan = int(plan)
        if step == exact.FINAL_PLAN_STEP:
            state.plan = 2
        view = exact.FarmView(observation)
        tape = policy.tapes[state.plan]
        action = deepcopy(tape[step])
        exact.repair_weeds(action, view, state, step)
        exact.subtract_advanced_sales(action, state, step)
        exact.advance_sales(action, view, state, tape, step)
        action["market"] = action["market"][: exact.MAX_ORDERS]
        action = exact.liquidate(view) if step == exact.LAST_STEP else action
        if state.plan == 10 and step == 360 and action["farmer"] == ["PICKUP", "WHEAT", 5]:
            action["farmer"][2] = 4
        return action

    return agent


def fixed_schedule(first: str, second: str):
    return {day: ([first] if day >= 3 else []) + ([second] if day >= 6 else []) for day in range(30)}


def held_inventory(observation, seat: int):
    private = observation["private"]
    total = Counter(private.get("shed", {}))
    for inventory in private.get("inventories", []):
        total.update(inventory)
    return {item: int(total.get(item, 0)) for item in PRODUCTS if total.get(item, 0)}


def tile_summary(farm):
    counts = farm_counts(farm)
    return {
        "land": len(farm.get("unlocked_quadrants", [])),
        "hands": len(farm.get("hands", [])),
        "wheat_tiles": int(counts["crops"].get("WHEAT", 0)),
        "major_crops": {item: int(counts["crops"].get(item, 0)) for item in ("CARROT", "TOMATO", "STRAWBERRY", "MELON")},
        "cows": int(counts["animals"].get("COW", 0)),
        "sheep": int(counts["animals"].get("SHEEP", 0)),
    }


def trajectory(replay, candidate_seat: int):
    timelines = [_economic_timeline(replay, player)[0] for player in (candidate_seat, 1 - candidate_seat)]
    rows = []
    for day in range(30):
        states = [state for state in replay["steps"] if int(state[candidate_seat]["observation"].get("day", 0)) == day]
        state = states[-1]
        record = {"day": day}
        for label, player, timeline in (
            ("candidate", candidate_seat, timelines[0]),
            ("opponent", 1 - candidate_seat, timelines[1]),
        ):
            obs = state[player]["observation"]
            farm = obs["farms"][player]
            prefix = timeline[: day + 1]
            purchases = Counter()
            sales = Counter()
            for item in prefix:
                purchases.update(item["seed_quantity"])
                purchases.update(item["product_quantity"])
                purchases.update(item["animal_quantity"])
                sales.update(item["sale_quantity"])
            record[label] = {
                "bank": float(farm["money"]),
                **tile_summary(farm),
                "inventory": held_inventory(obs, player),
                "cumulative_purchases": dict(purchases),
                "cumulative_sales": dict(sales),
            }
        record["bank_gap"] = record["candidate"]["bank"] - record["opponent"]["bank"]
        rows.append(record)
    return rows


def market_events(replay, candidate_seat: int):
    from analyze_top_player_replays import _transition_ledger

    events = []
    for index in range(1, len(replay["steps"])):
        previous = replay["steps"][index - 1]
        current = replay["steps"][index]
        ledgers, _ = _transition_ledger(previous, current, replay.get("configuration", {}))
        pre = previous[0]["observation"]["market"]
        post = current[0]["observation"]["market"]
        for product in PRODUCTS:
            candidate_qty = int(ledgers[candidate_seat]["sale_quantity"].get(product, 0))
            opponent_qty = int(ledgers[1 - candidate_seat]["sale_quantity"].get(product, 0))
            if not candidate_qty and not opponent_qty:
                continue
            events.append({
                "step": index - 1,
                "day": int(previous[0]["observation"].get("day", (index - 1) // 24)),
                "product": product,
                "candidate_quantity": candidate_qty,
                "opponent_quantity": opponent_qty,
                "candidate_revenue": float(ledgers[candidate_seat]["sale_revenue"].get(product, 0)),
                "opponent_revenue": float(ledgers[1 - candidate_seat]["sale_revenue"].get(product, 0)),
                "price_before": float(pre["prices"].get(product, 0)),
                "price_after": float(post["prices"].get(product, 0)),
                "inventory_before": int(pre["inventory"].get(product, 0)),
                "inventory_after": int(post["inventory"].get(product, 0)),
            })
    return events


def terminal_trace(replay, candidate_seat: int):
    rows = []
    for step in (648, 700, 711, 712, 713, 714, 715, 716, 717, 718, 719):
        state = replay["steps"][step]
        record = {"step": step}
        for label, player in (("candidate", candidate_seat), ("opponent", 1 - candidate_seat)):
            obs = state[player]["observation"]
            action = replay["steps"][step + 1][player].get("action") if step < 719 else None
            record[label] = {
                "bank": float(obs["farms"][player]["money"]),
                "inventory": held_inventory(obs, player),
                "terminal_mark_to_market": terminal_value(state, player),
                "issued_action": action,
            }
        rows.append(record)
    return rows


def execute(job):
    stage, candidate_name, opponent_name, seed, seat, forced_plan, fixed_pair = job
    started = time.perf_counter()
    candidate_module, candidate = load_agent(CANDIDATES[candidate_name], f"candidate_{stage}_{seed}_{seat}_{candidate_name}")
    if forced_plan is not None:
        candidate = forced_hardened(candidate_module, int(forced_plan))
    _, opponent = load_agent(OPPONENTS[opponent_name], f"opponent_{stage}_{seed}_{seat}_{opponent_name}")
    pair = [opponent, opponent]
    pair[seat] = candidate
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
    error = None
    try:
        if fixed_pair:
            _run_with_fixed_shops(env, pair, fixed_schedule(*fixed_pair))
        else:
            env.run(pair)
    except Exception as exc:
        error = repr(exc)
    if error or len(env.steps) != 720:
        return {
            "stage": stage, "candidate": candidate_name, "opponent": opponent_name,
            "seed": seed, "seat": seat, "forced_plan": forced_plan,
            "fixed_shop_pair": list(fixed_pair) if fixed_pair else None,
            "runtime_error": error or f"steps={len(env.steps)}", "elapsed_s": time.perf_counter() - started,
        }
    final = env.steps[-1]
    replay = env.toJSON()
    shop_pair = list(final[seat].observation["town"]["unlocked_shops"][:2])
    plan = forced_plan if forced_plan is not None else selected_plan(candidate_module, candidate, seat)
    own = float(final[seat].reward)
    other = float(final[1 - seat].reward)
    row = {
        "stage": stage, "candidate": candidate_name, "opponent": opponent_name,
        "seed": int(seed), "seat": int(seat), "shop_mode": "fixed" if fixed_pair else "natural",
        "shop_pair": shop_pair, "selected_plan": plan, "forced_plan": forced_plan,
        "fixed_shop_pair": list(fixed_pair) if fixed_pair else None,
        "runtime_error": None, "own_money": own, "opponent_money": other,
        "advantage": own - other,
        "outcome": "win" if own > other else "loss" if own < other else "tie",
        "candidate_economics": economic_summary(replay, seat),
        "opponent_economics": economic_summary(replay, 1 - seat),
        "candidate_terminal": terminal_value(final, seat),
        "opponent_terminal": terminal_value(final, 1 - seat),
        "elapsed_s": time.perf_counter() - started,
    }
    base_stage = stage.removesuffix("_1327")
    if candidate_name == "hardened" and base_stage in {"phase_a", "phase_b", "controls", "mirrors", "pizza"}:
        row["daily_trajectory"] = trajectory(replay, seat)
        row["market_events"] = market_events(replay, seat)
        row["terminal_trace"] = terminal_trace(replay, seat)
    return row


def jobs(stage: str):
    base_stage = stage.removesuffix("_1327")
    frozen = ("hardened", "exact", "previous_current_best", "v2")
    if base_stage == "phase_a":
        return [(stage, c, o, s, seat, None, None) for c in frozen for o in CURRENT_META for s in PHASE_A_SEEDS for seat in (0, 1)]
    if base_stage == "phase_b":
        return [(stage, c, o, s, seat, None, None) for c in frozen for o in CURRENT_META for s in PHASE_B_SEEDS for seat in (0, 1)]
    if base_stage == "controls":
        return [(stage, c, o, s, seat, None, None) for c in frozen for o in CONTROLS for s in CONTROL_SEEDS for seat in (0, 1)]
    if base_stage == "terminal":
        return [(stage, c, o, s, seat, None, None) for c in ("terminal_e182", "terminal_r31") for o in CURRENT_META for s in ORACLE_SEEDS for seat in (0, 1)]
    if base_stage == "mirrors":
        return [(stage, "hardened", o, PHASE_A_SEEDS[0], seat, None, None) for o in ("hardened_mirror", "exact_mirror") for seat in (0, 1)]
    if base_stage == "oracle":
        return [(stage, "hardened", o, s, seat, plan, None) for o in CURRENT_META for s in ORACLE_SEEDS for seat in (0, 1) for plan in range(13)]
    if base_stage == "pizza":
        pair = ("PIZZA_SHOP", "YARN_STORE")
        return [(stage, "hardened", o, s, seat, plan, pair) for o in CURRENT_META[:3] for s in PIZZA_SEEDS for seat in (0, 1) for plan in (7, 12)]
    raise KeyError(stage)


def run_stage(stage: str, workers: int):
    path = PARTIALS[stage]
    prior = json.loads(path.read_text()) if path.exists() else {"schema_version": 1, "stage": stage, "rows": []}
    rows = [row for row in prior["rows"] if not row.get("runtime_error")]
    done = {
        (r["candidate"], r["opponent"], r["seed"], r["seat"], r.get("forced_plan"), tuple(r.get("fixed_shop_pair") or ()))
        for r in rows
    }
    pending = [job for job in jobs(stage) if (job[1], job[2], job[3], job[4], job[5], tuple(job[6] or ())) not in done]
    if not pending:
        print(f"{stage}: already complete {len(rows)}/{len(jobs(stage))}")
        return
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(execute, job) for job in pending]
        for future in as_completed(futures):
            rows.append(future.result())
            if len(rows) % 4 == 0 or len(rows) == len(jobs(stage)):
                rows.sort(key=lambda r: (r["candidate"], r["opponent"], r["seed"], r["seat"], -1 if r.get("forced_plan") is None else r["forced_plan"]))
                path.write_text(json.dumps({"schema_version": 1, "stage": stage, "expected_games": len(jobs(stage)), "rows": rows}, indent=2, sort_keys=True) + "\n")
                print(f"{stage}: {len(rows)}/{len(jobs(stage))}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=tuple(PARTIALS) + ("all",))
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    stages = tuple(PARTIALS) if args.stage == "all" else (args.stage,)
    for stage in stages:
        run_stage(stage, args.workers)


if __name__ == "__main__":
    main()
