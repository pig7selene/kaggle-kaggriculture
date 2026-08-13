"""Replay-derived three-quadrant strawberry scaler with fourteen-hand peaks."""

from runpy import run_path


common = run_path("agents/router_replay_variant_common.py")
agent = common["make_variant"](labor_cap=14)

