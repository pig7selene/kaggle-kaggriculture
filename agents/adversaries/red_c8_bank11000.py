"""Retained red-team counter: staged eight cows with an 11k capital gate."""

from runpy import run_path


namespace = run_path("agents/early_compound_common.py")
config = dict(namespace["FROZEN_DAY14_CONFIG"])
config.update({
    "animal_count": 8,
    "animal_start_day": 11,
    "animal_schedule": ((11, 4), (16, 8)),
    "animal_start_mode": "day_and_bank",
    "animal_bank_threshold": 11000,
    "structure_start_day": 10,
    "animal_workers": 4,
    "land_purchase_days": (11,),
    "land_plots_per_quadrant": 12,
    "land_plots_per_added_hand": 2,
    "max_hands": 8,
})
agent = namespace["make_agent"](config)

