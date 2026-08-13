"""Replay-meta cow-only control using the scalable router."""

from runpy import run_path


common = run_path("agents/mixed_livestock_router_common.py")
agent = common["make_mixed_agent"](
    ((0, 1, 0), (5, 2, 0), (6, 3, 0), (7, 6, 0), (8, 8, 0), (15, 9, 0)),
    ("COW",) * 9,
)

