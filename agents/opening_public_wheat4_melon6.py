"""Replay opening allocation control: four wheat, six melons."""

from runpy import run_path

common = run_path("agents/opening_compound_common.py")
agent = common["make_opening_agent"](
    opening_pattern=("WHEAT",) * 4 + ("MELON",) * 6,
    feed_mode="hybrid",
    land_priority=True,
)
