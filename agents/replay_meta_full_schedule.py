"""Conservative cow-only implementation of the shared top-replay schedule.

The public policies also used sheep.  This candidate intentionally retains the
validated cow service architecture so the experiment tests the broader timing
principles without introducing a new mixed-animal router at the same time.
"""

from runpy import run_path


namespace = run_path("agents/replay_meta_common.py")
agent = namespace["make_replay_agent"](
    {
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
        "max_hands": 14,
    },
    animal_schedule=((0, 1), (5, 2), (6, 4), (7, 6), (8, 8), (15, 9)),
    crop_schedule=(
        (0, ("mixed", ("MELON", "WHEAT"))),
        (3, ("fixed", "STRAWBERRY")),
        (21, ("fixed", "WHEAT")),
    ),
    labor_caps=namespace["REPLAY_LABOR_CAPS"],
)

