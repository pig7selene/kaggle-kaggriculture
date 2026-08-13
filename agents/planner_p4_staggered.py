"""P4: P3 plus the cohort-search winner (S0 synchronized control).

The tested 2/3/4/planner cohort variants all regressed, so the controlled P4
architecture deliberately retains synchronized planting.
"""

from runpy import run_path

namespace = run_path("agents/planner_common.py")
config = dict(namespace["PLANNER_BASE"])
config.update({
    "planner_opponent_forecast": True,
    "planner_self_impact": True,
    "cohort_mode": "synchronized",
    "cohort_count": 1,
})
agent = namespace["make_agent"](config)
