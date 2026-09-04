"""Narrow livestock safety repair for complete Top-50 parent routes."""

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
SHED_TILES = {(4, 4), (5, 4), (4, 5), (5, 5)}


def make_safe(route_agent_path, exact_rescues=()):
    base = run_path(str(ROOT / route_agent_path))["agent"]
    exact_rescues = {tuple(value) for value in exact_rescues}

    def agent(obs):
        output = deepcopy(base(obs))
        player = obs["player"]
        farm = obs["farms"][player]
        positions = [farm["farmer"], *farm.get("hands", [])]
        inventories = obs["private"]["inventories"]
        actions = [output.get("farmer", ["PASS"]), *output.get("hands", [])]
        actions.extend([["PASS"]] * max(0, len(positions) - len(actions)))
        for index, position in enumerate(positions):
            x, y = position
            tile = farm["tiles"][y][x]
            if not isinstance(tile, dict) or not tile.get("animal") or tile.get("fed_today"):
                continue
            urgent = int(tile.get("consecutive_unfed", 0)) >= 1
            if not urgent:
                continue
            exact = (int(obs["step"]), int(x), int(y)) in exact_rescues
            if int(obs.get("hour", 0)) < 22 and not exact:
                continue
            if int(inventories[index].get("WHEAT", 0)) > 0:
                actions[index] = ["FEED"]
        output["farmer"], output["hands"] = actions[0], actions[1:len(positions)]
        return output

    agent.telemetry = base.telemetry
    agent.base = base
    agent.safety_policy = "hour-22 deadline or audited exact miss; co-located worker with carried wheat only"
    return agent
