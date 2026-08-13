"""P6: P5 plus the animal-capital search winner (fixed four cows).

Dynamic selection lost to the fixed-COW_4 control, so it is not forced into
the cumulative architecture.
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
})
agent = namespace["make_agent"](config)
