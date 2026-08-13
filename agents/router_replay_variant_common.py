"""Small controlled neighborhoods around the routed replay cow schedule."""

from runpy import run_path


REPLAY = run_path("agents/replay_meta_common.py")
ROUTER = run_path("agents/large_scale_router.py")
DEFAULT_ANIMALS = ((0, 1), (5, 2), (6, 4), (7, 6), (8, 8), (15, 9))


def make_variant(overrides=None, animal_schedule=DEFAULT_ANIMALS, labor_cap=14):
    config = {
        "structure_start_day": 0,
        "animal_workers": 4,
        "animal_selling": "immediate",
        "land_policy": "legacy",
        "forced_land_days": (6, 10),
        "enable_land": False,
        "quadrant_land_targets": True,
        "land_plots_per_quadrant": 25,
        "new_land_allocation": "adaptive",
        "fixed_hands": 4,
        "land_labor_mode": "staged",
        "land_plots_per_added_hand": 3,
        "max_hands": labor_cap,
    }
    if overrides:
        config.update(overrides)
    caps = tuple(min(labor_cap, value) for value in REPLAY["REPLAY_LABOR_CAPS"])
    base = REPLAY["make_replay_agent"](
        config,
        animal_schedule=animal_schedule,
        crop_schedule=(
            (0, ("mixed", ("MELON", "WHEAT"))),
            (3, ("fixed", "STRAWBERRY")),
            (21, ("fixed", "WHEAT")),
        ),
        labor_caps=caps,
    )
    return ROUTER["make_routed_agent"](base)

