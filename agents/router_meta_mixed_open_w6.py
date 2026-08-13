"""One-cow/four-sheep opening with six high-scale animal specialists."""

from runpy import run_path


common = run_path("agents/mixed_livestock_router_common.py")
agent = common["make_mixed_agent"](
    ((0, 1, 4), (5, 2, 4), (6, 3, 4), (7, 6, 4), (8, 8, 4), (15, 9, 4)),
    ("COW",) * 9 + ("SHEEP",) * 4,
    animal_workers=6,
)

