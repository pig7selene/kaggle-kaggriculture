"""P3: opponent-aware planner with marginal self-market impact."""

from runpy import run_path

namespace = run_path("agents/planner_common.py")
config = dict(namespace["PLANNER_BASE"])
config.update({"planner_opponent_forecast": True, "planner_self_impact": True})
agent = namespace["make_agent"](config)
