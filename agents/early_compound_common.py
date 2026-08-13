"""Thin experimental wrapper around the frozen C2 land engine.

The underlying engine is loaded read-only.  This wrapper adds only two research
controls: staged cow targets and an optional earlier melon harvest.  Keeping the
wrapper separate guarantees the historical day-14 agent remains byte-for-byte
and behaviorally frozen.
"""

from copy import deepcopy
from runpy import run_path


SOURCE_PATH = "agents/animal_land_common.py"
SOURCE = run_path(SOURCE_PATH)

ANIMALS = SOURCE["ANIMALS"]
BASE_PRICES = SOURCE["BASE_PRICES"]
CROPS = SOURCE["CROPS"]
LAND_COSTS = SOURCE["LAND_COSTS"]
C2_LAND_BASE = deepcopy(SOURCE["C2_LAND_BASE"])
_land_economics = SOURCE["_land_economics"]

FROZEN_DAY14_CONFIG = deepcopy(C2_LAND_BASE)
FROZEN_DAY14_CONFIG.update({
    "land_policy": "fixed",
    "land_purchase_days": (14,),
    "max_land_purchases": 1,
    "land_roi_hurdle": 0.0,
    "land_plots_per_quadrant": 12,
    "new_land_allocation": "adaptive",
    "land_labor_mode": "staged",
    "land_plots_per_added_hand": 4,
    "max_hands": 8,
})


def _accelerate_melon_age(obs, harvest_age):
    if harvest_age >= CROPS["MELON"]["peak"]:
        return obs
    changed = None
    day = obs["day"]
    me_index = obs["player"]
    for y, row in enumerate(obs["farms"][me_index]["tiles"]):
        for x, tile in enumerate(row):
            if not isinstance(tile, dict) or tile.get("kind") != "PLANT":
                continue
            if tile.get("crop") != "MELON" or tile.get("yield_units", 0) <= 0:
                continue
            actual_age = day - tile["planted_day"]
            if actual_age < harvest_age:
                continue
            if changed is None:
                changed = deepcopy(obs)
            changed_tile = changed["farms"][me_index]["tiles"][y][x]
            changed_tile["planted_day"] = day - CROPS["MELON"]["peak"]
    return changed if changed is not None else obs


def make_agent(overrides=None):
    config = deepcopy(FROZEN_DAY14_CONFIG)
    if overrides:
        config.update(deepcopy(overrides))

    schedule = tuple(config.get(
        "animal_schedule",
        ((config.get("animal_start_day", 11), config.get("animal_count", 4)),),
    ))
    schedule = tuple(sorted((int(day), int(count)) for day, count in schedule))
    first_day = schedule[0][0]
    agents = {}
    for _, count in schedule:
        resolved = deepcopy(config)
        resolved.pop("animal_schedule", None)
        resolved.pop("melon_harvest_age", None)
        resolved["animal_count"] = count
        resolved["animal_start_day"] = first_day
        agents[count] = SOURCE["make_agent"](resolved)

    melon_harvest_age = int(config.get("melon_harvest_age", CROPS["MELON"]["peak"]))

    def compound_agent(obs):
        target = schedule[0][1]
        for day, count in schedule:
            if obs["day"] >= day:
                target = count
        planning_obs = _accelerate_melon_age(obs, melon_harvest_age)
        action = agents[target](planning_obs)
        if config.get("semantic_validation", False):
            from test_economic_agents import _validate_action
            _validate_action(obs, action)
        return action

    compound_agent.config = config
    compound_agent.animal_schedule = schedule
    compound_agent.component_agents = agents
    return compound_agent
