"""Economic-engine control: fixed 12-plot melons with immediate selling."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "fixed",
    "fixed_crop": "MELON",
    "selling": "immediate",
})
