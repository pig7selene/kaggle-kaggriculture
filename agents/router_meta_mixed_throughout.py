"""Replay opening with modest later scaling of both cows and sheep."""

from runpy import run_path


common = run_path("agents/mixed_livestock_router_common.py")
agent = common["make_mixed_agent"](
    (
        (0, 1, 4), (5, 2, 4), (6, 3, 4), (7, 6, 4), (8, 8, 4),
        (12, 8, 5), (15, 9, 6),
    ),
    ("COW",) * 9 + ("SHEEP",) * 6,
)

