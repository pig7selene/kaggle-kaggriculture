"""Conservative market-only residual with bounded future SELL-slot assignment.

This keeps the frozen portfolio's complete route intact.  It may pull a
route-planned batch forward into an already existing SELL slot when the
calibrated public hazard model and exact own-market simulation show a large
capital benefit, then restores the displaced batch at its original future
slot.  No crop, animal, land, labor, or movement action is changed.
"""

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
BASE = run_path(str(ROOT / "agents/top50_distilled/top50_observable_portfolio.py"))["agent"]
COMMON = run_path(str(ROOT / "agents/v27_backbone_common.py"))
ASSIGN = COMMON["_future_slot_assignment"]
HAZARD = COMMON["_opponent_hazard"]

telemetry = {
    "calls": 0,
    "assignments": 0,
    "restored": 0,
    "errors": 0,
}
reservations = {}


def _reset():
    reservations.clear()
    telemetry.clear()
    telemetry.update({"calls": 0, "assignments": 0, "restored": 0, "errors": 0})


def _route_actions():
    parent_name = BASE.telemetry.get("portfolio_parent")
    if parent_name in getattr(BASE, "parents", {}):
        parent = BASE.parents[parent_name]
        base = getattr(parent, "base", None)
        route = getattr(base, "route", None)
        if route:
            return route.get("consensus_actions", route.get("actions", []))
    return None


def agent(obs):
    if int(obs.get("step", 0)) == 0:
        _reset()
    telemetry["calls"] += 1
    action = deepcopy(BASE(obs))
    step = int(obs.get("step", 0))
    route_actions = _route_actions()
    if not route_actions or not action.get("market"):
        return action
    try:
        # Honor an already displaced batch only at its exact existing slot.
        for index, order in enumerate(action["market"]):
            replacement = reservations.pop((step, index), None)
            if replacement and order and order[0] == "SELL":
                if obs["private"]["shed"].get(replacement[1], 0) > 0:
                    action["market"][index] = replacement
                    telemetry["restored"] += 1
        action["market"], changed = ASSIGN(
            obs,
            action["market"],
            route_actions,
            reservations,
            hazard=HAZARD(obs),
        )
        telemetry["assignments"] += int(changed)
    except Exception:
        telemetry["errors"] += 1
    return action


agent.telemetry = telemetry
agent.base = BASE
agent.policy = "bounded public-hazard future assignment among existing SELL slots"
