"""Hire-timing control with three rather than four day-0 hands."""

from runpy import run_path

common = run_path("agents/opening_compound_common.py")
caps = list(common["REPLAY"]["REPLAY_LABOR_CAPS"])
caps[0] = 3
agent = common["make_opening_agent"](
    feed_mode="hybrid", land_priority=True, labor_caps=tuple(caps)
)
