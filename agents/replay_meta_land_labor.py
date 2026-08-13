"""C8 crops/animals with the public-meta land and labor schedule only."""

from runpy import run_path


namespace = run_path("agents/replay_meta_common.py")
agent = namespace["make_replay_agent"](
    {
        "animal_count": 8,
        "animal_start_day": 12,
        "structure_start_day": 11,
        "animal_workers": 4,
        # Forced days reproduce the observed aggressive reinvestment rule.  A
        # purchase still requires the actual land cost to be in the bank.
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
    labor_caps=namespace["REPLAY_LABOR_CAPS"],
)

