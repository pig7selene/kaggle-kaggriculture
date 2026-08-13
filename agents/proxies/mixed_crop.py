"""Proxy: diversified fixed crop portfolio."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "mixed",
    "mixed_pattern": ("MELON", "WHEAT", "TOMATO", "STRAWBERRY", "CARROT"),
    "base_plots": 20, "max_plots": 20, "fixed_hands": 3,
    "selling": "immediate",
})
