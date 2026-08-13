"""Retained adversary: six cows targeted from day 8, land from day 11."""

from runpy import run_path

namespace = run_path("agents/planner_common.py")
config = dict(namespace["CURRENT_BEST_CONFIG"])
config.update({
    "animal_count": 6,
    "animal_start_day": 8,
    "structure_start_day": 7,
    "animal_workers": 3,
    "land_purchase_days": (11,),
    "selling": "aware",
})
agent = namespace["make_agent"](config)

