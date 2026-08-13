"""Feed-capital control with a two-day daily wheat reserve."""

from runpy import run_path

common = run_path("agents/opening_compound_common.py")
agent = common["make_opening_agent"](
    feed_mode="daily", wheat_reserve_days=2, land_priority=True
)
