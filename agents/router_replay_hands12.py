"""Routed replay economy capped at twelve hired hands."""

from runpy import run_path


common = run_path("agents/router_replay_variant_common.py")
agent = common["make_variant"](labor_cap=12)

