"""Five-sheep cash opening followed by cow scaling."""

from runpy import run_path


common = run_path("agents/mixed_livestock_router_common.py")
agent = common["make_mixed_agent"](
    ((0, 0, 5), (5, 1, 5), (6, 3, 5), (7, 6, 5), (8, 8, 5)),
    ("SHEEP",) * 5 + ("COW",) * 8,
)

