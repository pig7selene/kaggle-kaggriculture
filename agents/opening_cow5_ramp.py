"""Five-cow day-0 control without sheep."""

from runpy import run_path

common = run_path("agents/opening_compound_common.py")
agent = common["make_opening_agent"](
    schedule=((0, 5, 0), (7, 6, 0), (8, 8, 0), (15, 9, 0)),
    feed_mode="hybrid",
    land_priority=True,
)
