"""Isolated feed-before-expansion correctness ablation for the routed agent.

When any existing cow is still unfed, animal specialists service only occupied
pastures.  Building and placing additional scheduled cows resumes as soon as
the existing herd is safe.  No crop, market, land, labor, or territory-routing
parameter is changed.
"""

from copy import deepcopy
from runpy import run_path


namespace = run_path("agents/router_replay_hands12.py")
agent = namespace["agent"]
router_globals = agent.__globals__
original_animal_action = router_globals["_animal_action"]


def _feed_first_animal_action(
    obs, unit_index, position, inventory, assigned, config, reserved, resources
):
    me = obs["farms"][obs["player"]]
    any_unfed = any(
        isinstance(tile, dict)
        and tile.get("animal")
        and not tile.get("fed_today", False)
        for row in me["tiles"] for tile in row
    )
    if any_unfed and obs["day"] < 29:
        occupied = tuple(
            (target, animal)
            for target, animal in assigned
            if isinstance(me["tiles"][target[1]][target[0]], dict)
            and me["tiles"][target[1]][target[0]].get("animal")
        )
        safe_config = deepcopy(config)
        safe_config["animal_count"] = 0
        safe_config.pop("mixed_animal_positions", None)
        return original_animal_action(
            obs,
            unit_index,
            position,
            inventory,
            occupied,
            safe_config,
            reserved,
            resources,
        )
    return original_animal_action(
        obs, unit_index, position, inventory, assigned, config, reserved, resources
    )


router_globals["_animal_action"] = _feed_first_animal_action

