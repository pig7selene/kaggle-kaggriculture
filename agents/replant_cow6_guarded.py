"""Six-cow lifecycle control with state-preserving animal no-op suppression."""

from copy import deepcopy
from runpy import run_path


base = run_path("agents/replant_cow6_control.py")["agent"]


def agent(obs):
    action = deepcopy(base(obs))
    me = obs["farms"][obs["player"]]
    positions = [tuple(me["farmer"]), *[tuple(value) for value in me["hands"]]]
    unit_actions = [action["farmer"], *action["hands"]]
    claimed = set()
    for index, (position, unit_action) in enumerate(zip(positions, unit_actions)):
        tile = me["tiles"][position[1]][position[0]]
        if not isinstance(tile, dict) or not tile.get("animal"):
            continue
        op = unit_action[0]
        key = (position, op)
        invalid = (
            (op in {"COLLECT_FERTILIZER", "CARE", "FEED", "HARVEST"} and key in claimed)
            or
            (op == "COLLECT_FERTILIZER" and not tile.get("fertilizer_available", False))
            or (op == "CARE" and tile.get("cared_today", False))
            or (op == "FEED" and tile.get("fed_today", False))
            or (op == "HARVEST" and tile.get("yield_units", 0) <= 0)
        )
        if invalid:
            unit_actions[index] = ["PASS"]
        elif op in {"COLLECT_FERTILIZER", "CARE", "FEED", "HARVEST"}:
            claimed.add(key)
    action["farmer"] = unit_actions[0]
    action["hands"] = unit_actions[1:]
    return action


agent.config = getattr(base, "config", {})
agent.base_agent = base
