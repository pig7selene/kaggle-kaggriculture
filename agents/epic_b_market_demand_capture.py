"""Controlled Pedro mechanism: bounded visible-demand wheat capture."""

from runpy import run_path

common = run_path("agents/epic_candidate_common.py")
agent = common["demand_capture_wrapper"](common["make_candidate"]())
