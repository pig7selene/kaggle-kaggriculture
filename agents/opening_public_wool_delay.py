"""Animal-sale control: hold first wool until day 7."""

from runpy import run_path

common = run_path("agents/opening_compound_common.py")
agent = common["make_opening_agent"](
    feed_mode="hybrid",
    land_priority=True,
    hold_sales_until={"WOOL": 7},
)
