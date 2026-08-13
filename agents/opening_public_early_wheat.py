"""First-harvest timing control: harvest wheat from age two."""

from runpy import run_path

common = run_path("agents/opening_compound_common.py")
agent = common["make_opening_agent"](
    feed_mode="hybrid", land_priority=True, wheat_harvest_age=2
)
