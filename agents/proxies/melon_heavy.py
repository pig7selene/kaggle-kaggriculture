"""Proxy: concentrated 18-plot melon production."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "fixed", "fixed_crop": "MELON", "base_plots": 18,
    "max_plots": 18, "fixed_hands": 2, "selling": "immediate",
})
