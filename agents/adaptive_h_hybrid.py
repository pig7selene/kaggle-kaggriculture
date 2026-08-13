"""Tuned hybrid: phased defaults with economic crop overrides."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "hybrid",
    "phase_schedule": ((0, "MELON"), (11, "STRAWBERRY"), (21, "WHEAT")),
    "hybrid_deviation": 1.30,
    "selling": "aware",
    "allocation_limits": {
        "MELON": 1.00,
        "STRAWBERRY": 1.00,
        "TOMATO": 0.34,
        "CARROT": 1.00,
        "WHEAT": 1.00,
    },
})
