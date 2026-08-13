"""P5: P4 plus the winning planner-selected selling horizon."""

from runpy import run_path

namespace = run_path("agents/planner_common.py")
config = dict(namespace["PLANNER_BASE"])
config.update({
    "planner_opponent_forecast": True,
    "planner_self_impact": True,
    "cohort_mode": "synchronized",
    "cohort_count": 1,
    "selling_horizon": "planner",
})
agent = namespace["make_agent"](config)
