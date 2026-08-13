"""Replay-meta sheep-only controlled candidate."""

from runpy import run_path


common = run_path("agents/mixed_livestock_router_common.py")
agent = common["make_mixed_agent"](
    ((0, 0, 5), (5, 0, 6), (6, 0, 7), (7, 0, 10), (8, 0, 12), (15, 0, 13)),
    ("SHEEP",) * 13,
)

