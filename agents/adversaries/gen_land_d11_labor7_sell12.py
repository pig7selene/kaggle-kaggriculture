"""Retained adversary: day-11 16-plot land, seven hands, 12-turn selling."""

from runpy import run_path

namespace = run_path("agents/planner_common.py")
config = dict(namespace["CURRENT_BEST_CONFIG"])
config.update({
    "land_purchase_days": (11,),
    "land_plots_per_quadrant": 16,
    "land_plots_per_added_hand": 3,
    "max_hands": 7,
    "selling_horizon": 12,
    "planner_opponent_forecast": True,
})
agent = namespace["make_agent"](config)

