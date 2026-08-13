"""P2: full-farm planner plus visible-opponent production forecasting."""

from runpy import run_path

namespace = run_path("agents/planner_common.py")
config = dict(namespace["PLANNER_BASE"])
config.update({"planner_opponent_forecast": True, "planner_self_impact": False})
agent = namespace["make_agent"](config)
