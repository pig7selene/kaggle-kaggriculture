"""Retained adversary: earliest feasible 16-plot land with six hands."""

from runpy import run_path

namespace = run_path("agents/planner_common.py")
config = dict(namespace["CURRENT_BEST_CONFIG"])
config.update({
    "land_purchase_days": (8,),
    "land_plots_per_quadrant": 16,
    "land_plots_per_added_hand": 4,
    "max_hands": 6,
    "selling_horizon": 0,
    "planner_opponent_forecast": True,
})
agent = namespace["make_agent"](config)

