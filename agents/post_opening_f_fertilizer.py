"""F: frozen public opening with mature-strawberry fertilizer use only."""

from runpy import run_path

common = run_path("agents/opening_compound_common.py")
caps = list(common["REPLAY"]["REPLAY_LABOR_CAPS"])
caps[0] = 5
agent = common["make_opening_agent"](
    schedule=((0, 1, 4), (5, 2, 4), (6, 8, 4), (15, 9, 4)),
    feed_mode="hybrid",
    land_priority=True,
    labor_caps=tuple(caps),
    post_config={"crop_fertilizer": True, "fertilizer_reserve": 12},
)
