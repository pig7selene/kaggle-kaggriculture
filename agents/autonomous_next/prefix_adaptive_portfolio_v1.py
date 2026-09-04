"""Safe prefix-compatible route selector (research candidate).

The frozen Top-50 portfolio commits to a complete route at step 1.  This
candidate keeps that commitment until step 72, where a small set of raw routes
has an identical action prefix.  Only routes whose replay actions are exactly
identical through the switch point are eligible, so the farm state and all
crop/animal/labor commitments remain coherent.  At step 72 the continuation
is selected from the live market and visible opponent production.  No route
is ever spliced across an incompatible prefix.

This is intentionally a narrow research probe, not a deployment agent.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
ROUTE_BANK = json.loads((ROOT / "experiments/top50_route_bank.json").read_text())

# The selector's three anchors match the frozen portfolio's complete parents.
ANCHOR_IDS = {
    "dmitry": "super_raw_55859516",
    "hanserong": "super_raw_55886665",
    "redblack": "super_raw_55890191",
}

# All five routes below share the exact consensus action prefix through turn
# 71.  The hanserong route has no compatible alternative at that checkpoint.
PREFIX_GROUPS = {
    "super_raw_55859516": (
        "super_raw_55859516",
        "super_raw_55890191",
        "super_raw_55904387",
        "super_raw_55871126",
        "super_raw_55885628",
    ),
    "super_raw_55890191": (
        "super_raw_55859516",
        "super_raw_55890191",
        "super_raw_55904387",
        "super_raw_55871126",
        "super_raw_55885628",
    ),
    "super_raw_55886665": ("super_raw_55886665",),
}
SWITCH_STEP = 72

BASE_PRICES = {
    "WHEAT": 25,
    "CARROT": 35,
    "TOMATO": 60,
    "STRAWBERRY": 120,
    "MELON": 250,
    "EGG": 50,
    "MILK": 160,
    "WOOL": 200,
    "FERTILIZER": 100,
}
ANIMAL_PRODUCT = {"GOOSE": "EGG", "COW": "MILK", "SHEEP": "WOOL"}

ROUTES = {row["route_id"]: row for row in ROUTE_BANK["routes"]}


def _load_agent(route_id):
    path = ROOT / "agents" / "top50_distilled" / "raw" / f"{route_id}.py"
    module = run_path(str(path))
    agent = module.get("agent")
    if not callable(agent):
        raise RuntimeError(f"route does not expose agent: {route_id}")
    return agent


# Only routes that can be anchors or valid prefix-compatible continuations need
# to be warmed.  Keeping the route bank metadata broad is useful for scoring,
# but warming all 23 complete executors would add needless per-turn latency.
_WARM_IDS = set(ANCHOR_IDS.values())
for _group in PREFIX_GROUPS.values():
    _WARM_IDS.update(_group)
ROUTE_AGENTS = {route_id: _load_agent(route_id) for route_id in sorted(_WARM_IDS)}


def _reset_state(state, telemetry):
    state.clear()
    state.update({"last_step": -1, "anchor": None, "selected": None, "switched": False})
    telemetry.clear()
    telemetry.update({
        "calls": 0,
        "anchor": None,
        "selected": None,
        "switch_step": None,
        "switches": 0,
        "scores": {},
        "prefix_verified": True,
    })


def _select_anchor(obs):
    """Use the frozen observable step-1 rule for the initial route."""
    other = obs["farms"][1 - obs["player"]]
    money = float(other.get("money", 0))
    hands = len(other.get("hands", []))
    if money >= 2500 and hands == 0:
        return "redblack"
    if money >= 1500 and hands >= 6:
        return "hanserong"
    if 3 < money <= 10 and hands >= 5:
        return "hanserong"
    return "dmitry"


def _opponent_pressure(obs):
    """Estimate visible near-term product pressure from the opponent farm."""
    farm = obs["farms"][1 - obs["player"]]
    pressure = {item: 0.0 for item in BASE_PRICES}
    for row in farm.get("tiles", []):
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crop = tile.get("crop")
                if crop in pressure:
                    pressure[crop] += 1.0
            product = ANIMAL_PRODUCT.get(tile.get("animal"))
            if product:
                pressure[product] += 1.5
                pressure["FERTILIZER"] += 0.5
    return pressure


def _route_score(obs, route_id, start=SWITCH_STEP):
    """Score only already committed future sales, at current observable quotes.

    The score is deliberately ordinal: current price/base rewards a route's
    product mix, while visible opponent capacity and current market inventory
    penalize products likely to glut.  It does not invent future prices or
    alter any route action.
    """
    route = ROUTES[route_id]
    prices = obs.get("market", {}).get("prices", {})
    inventory = obs.get("market", {}).get("inventory", {})
    pressure = _opponent_pressure(obs)
    score = 0.0
    for step_action in route.get("consensus_actions", route.get("actions", []))[start:]:
        for order in step_action.get("market", []):
            if not isinstance(order, list) or len(order) < 3 or order[0] != "SELL":
                continue
            item, quantity = order[1], max(0, int(order[2]))
            base = float(BASE_PRICES.get(item, 1))
            quote = float(prices.get(item, base))
            # Inventory is centered at 10,000 in the simulator.  Use a small
            # bounded penalty so prices remain the primary live signal.
            excess = max(0.0, float(inventory.get(item, 10000)) - 10000.0) / 10000.0
            pressure_penalty = min(0.35, 0.012 * pressure.get(item, 0.0))
            score += quantity * (quote / base - 0.20 * excess - pressure_penalty)
    # Keep scores comparable even when one route has a small terminal batch.
    return score


def _verified_group(anchor_id):
    group = PREFIX_GROUPS.get(anchor_id, (anchor_id,))
    anchor = ROUTES[anchor_id].get("consensus_actions", ROUTES[anchor_id]["actions"])
    verified = []
    for route_id in group:
        route = ROUTES.get(route_id)
        if route is None:
            continue
        actions = route.get("consensus_actions", route["actions"])
        if actions[:SWITCH_STEP] == anchor[:SWITCH_STEP]:
            verified.append(route_id)
    return tuple(verified) or (anchor_id,)


def agent(obs):
    """Emit one valid action while preserving a coherent complete route."""
    state = getattr(agent, "_state", None)
    telemetry = getattr(agent, "telemetry", None)
    if state is None:
        state, telemetry = {}, {}
        agent._state = state
        agent.telemetry = telemetry
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)):
        _reset_state(state, telemetry)

    telemetry["calls"] += 1
    state["last_step"] = step

    # Warm every route on every observation.  A route can be selected later
    # only because its prefix has been executed identically to this point;
    # warming keeps its worker-mapping state synchronized for a safe switch.
    outputs = {route_id: ROUTE_AGENTS[route_id](obs) for route_id in ROUTE_AGENTS}

    if state["anchor"] is None and step >= 1:
        anchor_name = _select_anchor(obs)
        state["anchor"] = ANCHOR_IDS[anchor_name]
        telemetry["anchor"] = state["anchor"]
        state["selected"] = state["anchor"]
        telemetry["selected"] = state["selected"]

    if state["anchor"] is None:
        # All routes have the documented PASS at step 0; dmitry is the frozen
        # portfolio's deterministic warm-up output.
        return deepcopy(outputs[ANCHOR_IDS["dmitry"]])

    if step == SWITCH_STEP and not state["switched"]:
        candidates = _verified_group(state["anchor"])
        scored = {route_id: _route_score(obs, route_id) for route_id in candidates}
        anchor_score = scored.get(state["anchor"], float("-inf"))
        # Require a meaningful live signal before leaving the anchor.  This
        # avoids turning tiny quote noise into a route change.
        chosen = max(candidates, key=lambda rid: (scored[rid], rid))
        if scored[chosen] - anchor_score < 0.75:
            chosen = state["anchor"]
        state["selected"] = chosen
        state["switched"] = True
        telemetry["switch_step"] = step
        telemetry["switches"] = int(chosen != state["anchor"])
        telemetry["scores"] = scored
        telemetry["selected"] = chosen

    selected = state["selected"] or ANCHOR_IDS["dmitry"]
    telemetry["selected"] = selected
    return deepcopy(outputs[selected])


agent._state = {}
agent.telemetry = {}
agent.description = "Prefix-compatible day-3 market-aware complete-route selector"
agent.switch_step = SWITCH_STEP
agent.prefix_groups = PREFIX_GROUPS
