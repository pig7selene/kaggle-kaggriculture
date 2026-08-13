"""Replay-derived early staple turnover followed by premium crop scaling."""

from runpy import run_path


replay = run_path("agents/replay_meta_common.py")
router = run_path("agents/large_scale_router.py")
base = replay["make_replay_agent"](
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
        (0, ("fixed", "WHEAT")),
        (4, ("mixed", ("MELON", "WHEAT"))),
        (11, ("fixed", "STRAWBERRY")),
        (21, ("fixed", "WHEAT")),
    ),
    labor_caps=replay["REPLAY_LABOR_CAPS"],
)
agent = router["make_routed_agent"](base)

