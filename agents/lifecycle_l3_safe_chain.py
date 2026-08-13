"""L3: stationary replant chaining with time reserved for first watering."""

from runpy import run_path

common = run_path("agents/opening_compound_common.py")
caps = list(common["REPLAY"]["REPLAY_LABOR_CAPS"])
caps[0] = 5
agent = common["make_opening_agent"](
    schedule=((0, 1, 4), (5, 2, 4), (6, 8, 4), (15, 9, 4)),
    feed_mode="hybrid", land_priority=True, labor_caps=tuple(caps),
    post_config={"chain_replant": True, "chain_last_hour": 21},
)
