"""P1: marginal full-farm crop planner without opponent/self forecasts."""

from runpy import run_path

namespace = run_path("agents/planner_common.py")
config = dict(namespace["PLANNER_BASE"])
config.update({"planner_opponent_forecast": False, "planner_self_impact": False})
agent = namespace["make_agent"](config)
