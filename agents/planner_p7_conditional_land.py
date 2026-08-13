"""P7: P6 plus the conditional-land search winner (one quadrant only).

No tested second-expansion gate fired profitably, so the cumulative candidate
retains the established single day-14 purchase.
"""

from runpy import run_path

namespace = run_path("agents/planner_common.py")
config = dict(namespace["PLANNER_BASE"])
config.update({
    "planner_opponent_forecast": True,
    "planner_self_impact": True,
    "cohort_mode": "synchronized",
    "cohort_count": 1,
    "selling_horizon": "planner",
    "dynamic_animal_capital": False,
    "animal_type": "COW",
    "animal_count": 4,
    "animal_portfolio": [],
    "max_land_purchases": 1,
})
agent = namespace["make_agent"](config)
