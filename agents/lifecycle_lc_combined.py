"""LC: ready ongoing harvests plus safe stationary replant chaining.

This candidate intentionally preserves the frozen opening and all economic
decisions from opening_public_front_cow8_day6.  Only post-day-10 crop task
ordering and the harvest-to-replant handoff are enabled.
"""

from runpy import run_path

common = run_path("agents/opening_compound_common.py")
caps = list(common["REPLAY"]["REPLAY_LABOR_CAPS"])
caps[0] = 5
agent = common["make_opening_agent"](
    schedule=((0, 1, 4), (5, 2, 4), (6, 8, 4), (15, 9, 4)),
    feed_mode="hybrid", land_priority=True, labor_caps=tuple(caps),
    post_config={
        "harvest_policy": "ready_ongoing",
        "harvest_priority": 0.75,
        "chain_replant": True,
        "chain_last_hour": 21,
    },
)
