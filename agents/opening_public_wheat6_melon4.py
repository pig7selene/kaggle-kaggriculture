"""Replay opening allocation control: six wheat, four melons."""

from runpy import run_path

common = run_path("agents/opening_compound_common.py")
agent = common["make_opening_agent"](
    opening_pattern=("WHEAT",) * 6 + ("MELON",) * 4,
    feed_mode="hybrid",
    land_priority=True,
)
