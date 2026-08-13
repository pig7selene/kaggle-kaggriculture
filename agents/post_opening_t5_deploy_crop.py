"""T5: combine proven deployment priority with the replay crop phases."""

from runpy import run_path

common = run_path("agents/opening_compound_common.py")
caps = list(common["REPLAY"]["REPLAY_LABOR_CAPS"])
caps[0] = 5
phase_pattern = common["make_opening_agent"](
    schedule=((0, 1, 4),), labor_caps=tuple(caps)
).base_agent.components["opening"].crop_schedule[0][1][1]
agent = common["make_opening_agent"](
    schedule=((0, 1, 4), (5, 2, 4), (6, 8, 4), (15, 9, 4)),
    feed_mode="hybrid",
    land_priority=True,
    labor_caps=tuple(caps),
    post_crop_schedule=(
        (0, ("mixed", phase_pattern)),
        (11, ("mixed", ("WHEAT", "MELON", "STRAWBERRY", "STRAWBERRY", "STRAWBERRY"))),
        (16, ("mixed", ("WHEAT", "WHEAT", "STRAWBERRY", "STRAWBERRY", "STRAWBERRY"))),
        (21, ("fixed", "WHEAT")),
    ),
    post_config={"plant_priority": 1.5},
)
