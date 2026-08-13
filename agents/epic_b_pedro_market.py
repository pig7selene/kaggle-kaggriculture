"""Replay-faithful Pedro wheat inventory-cycle ablation on the frozen field agent."""

from runpy import run_path

common = run_path("agents/epic_candidate_common.py")
agent = common["oscillating_wheat_market_maker"](common["make_candidate"]())
