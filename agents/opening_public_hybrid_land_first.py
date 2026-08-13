"""Public mixed opening with risk feed, then daily feed, and deed priority."""

from runpy import run_path


common = run_path("agents/opening_compound_common.py")
agent = common["make_opening_agent"](feed_mode="hybrid", land_priority=True)
