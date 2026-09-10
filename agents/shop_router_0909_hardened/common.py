"""Surgical Plan-10 patch harness around the exact public reproduction.

The public Shop Router 0909 implementation and action payload remain untouched
under ``agents/shop_router_0909``.  Each factory call loads an isolated copy of
that exact Apache-2.0 implementation, then changes one primitive only when the
active route is Plan 10.  See NOTICE.md and the experiment patch manifest.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import time


EXACT_MAIN = Path(__file__).resolve().parents[1] / "shop_router_0909" / "main.py"


def _load_exact(tag):
    name = f"shop_router_0909_exact_{tag}_{time.time_ns()}"
    spec = importlib.util.spec_from_file_location(name, EXACT_MAIN)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load exact parent at {EXACT_MAIN}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_agent(patch_id):
    """Return a state-isolated exact agent with one declared Plan-10 edit."""
    exact = _load_exact(patch_id)

    def agent(observation, configuration=None):
        action = exact.agent(observation, configuration)
        step = int(observation["step"])
        player = int(observation["player"])
        plan = exact._POLICY.players[player].plan
        if plan != 10:
            return action

        if patch_id == "reserve_sale" and step == 332:
            for order in action["market"]:
                if order == ["SELL", "WHEAT", 9]:
                    order[2] = 8
                    break
        elif patch_id == "buy_one" and step == 335:
            action["market"].append(["BUY_PRODUCT", "WHEAT", 1])
        elif patch_id == "reallocate_day14" and step == 339:
            if action["hands"] and action["hands"][0] == ["PICKUP", "WHEAT", 5]:
                action["hands"][0][2] = 4
        elif patch_id == "reallocate_day15" and step == 360:
            if action["farmer"] == ["PICKUP", "WHEAT", 5]:
                action["farmer"][2] = 4
        return action

    agent.patch_id = patch_id
    agent.exact_module = exact
    return agent
