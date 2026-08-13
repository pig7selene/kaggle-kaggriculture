"""C0: unchanged phased crop baseline for animal-policy controls."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "phased",
    "phase_schedule": ((0, "MELON"), (11, "STRAWBERRY"), (21, "WHEAT")),
    "selling": "immediate",
})
