"""First-sale control: hold fertilizer until day 3."""

from runpy import run_path

common = run_path("agents/opening_compound_common.py")
agent = common["make_opening_agent"](
    feed_mode="hybrid",
    land_priority=True,
    hold_sales_until={"FERTILIZER": 3},
)
