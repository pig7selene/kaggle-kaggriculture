"""Helpers for the controlled top-replay policy ablations.

This module deliberately wraps the frozen C8/C2 land engine instead of
changing it.  The replay experiments need two controls that the historical
engine did not expose directly: a day-specific labor ceiling and crop-mode
transitions.  Both controls select/filter existing engine behavior; routing,
animal service, selling, and endgame handling remain in the frozen engine.
"""

from copy import deepcopy
from runpy import run_path


ENGINE = run_path("agents/early_compound_common.py")
SOURCE = ENGINE["SOURCE"]
FROZEN_C8_CONFIG = deepcopy(ENGINE["FROZEN_DAY14_CONFIG"])

# Median maximum hands observed by day across the 35 selected top-player
# appearances.  These are daily hands (not counting the main farmer).
REPLAY_LABOR_CAPS = (
    4, 1, 2, 3, 3, 3, 4, 7, 6, 7,
    14, 10, 10, 8, 9, 9, 13, 9, 11, 13,
    14, 12, 10, 14, 11, 12, 12, 10, 10, 10,
)


def _active_value(schedule, day):
    value = schedule[0][1]
    for start_day, candidate in schedule:
        if day >= start_day:
            value = candidate
    return value


def make_replay_agent(
    overrides,
    *,
    animal_schedule=((12, 8),),
    crop_schedule=((0, ("phased", None)),),
    labor_caps=None,
):
    """Build a scheduled agent from immutable engine components.

    ``crop_schedule`` entries contain ``(day, (mode, value))``.  ``value`` is
    the fixed crop for fixed mode or the repeating tuple for mixed mode.
    Existing plants are never dug merely because a phase changes.
    """

    base = deepcopy(FROZEN_C8_CONFIG)
    base.update(deepcopy(overrides))
    animal_schedule = tuple(sorted((int(day), int(count)) for day, count in animal_schedule))
    crop_schedule = tuple(sorted((int(day), value) for day, value in crop_schedule))
    first_animal_day = animal_schedule[0][0]

    components = {}
    for _, animal_count in animal_schedule:
        for _, (crop_mode, crop_value) in crop_schedule:
            config = deepcopy(base)
            config.pop("animal_schedule", None)
            config["animal_count"] = animal_count
            config["animal_start_day"] = first_animal_day
            config["crop_mode"] = crop_mode
            if crop_mode == "fixed":
                config["fixed_crop"] = crop_value
            elif crop_mode == "mixed":
                config["mixed_pattern"] = tuple(crop_value)
            components[(animal_count, crop_mode, crop_value)] = SOURCE["make_agent"](config)

    def replay_agent(obs):
        animal_count = _active_value(animal_schedule, obs["day"])
        crop_mode, crop_value = _active_value(crop_schedule, obs["day"])
        action = components[(animal_count, crop_mode, crop_value)](obs)
        if labor_caps is None:
            return action

        cap = int(labor_caps[min(obs["day"], len(labor_caps) - 1)])
        next_hire = int(obs["farms"][obs["player"]].get("hires_today", 0))
        filtered_market = []
        for order in action["market"]:
            if order[0] != "HIRE":
                filtered_market.append(order)
                continue
            if next_hire < cap:
                filtered_market.append(order)
                next_hire += 1
        action["market"] = filtered_market
        return action

    def active_config(obs):
        animal_count = _active_value(animal_schedule, obs["day"])
        crop_mode, crop_value = _active_value(crop_schedule, obs["day"])
        return components[(animal_count, crop_mode, crop_value)].config

    replay_agent.config = base
    replay_agent.animal_schedule = animal_schedule
    replay_agent.crop_schedule = crop_schedule
    replay_agent.labor_caps = labor_caps
    replay_agent.components = components
    replay_agent.active_config = active_config
    return replay_agent
