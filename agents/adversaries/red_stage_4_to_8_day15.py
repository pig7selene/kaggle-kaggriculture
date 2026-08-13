"""Retained red-team counter: four day-11 cows, eight from day 15."""

from runpy import run_path


namespace = run_path("agents/early_compound_common.py")
config = dict(namespace["FROZEN_DAY14_CONFIG"])
config.update({
    "animal_count": 8,
    "animal_start_day": 11,
    "animal_schedule": ((11, 4), (15, 8)),
    "structure_start_day": 0,
    "animal_workers": 4,
    "land_purchase_days": (11,),
    "land_plots_per_quadrant": 12,
    "land_plots_per_added_hand": 2,
    "max_hands": 8,
})
agent = namespace["make_agent"](config)

