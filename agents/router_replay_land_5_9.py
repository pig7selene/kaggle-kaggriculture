"""Routed replay economy with land targets one day earlier."""

from runpy import run_path


common = run_path("agents/router_replay_variant_common.py")
agent = common["make_variant"]({"forced_land_days": (5, 9)})

