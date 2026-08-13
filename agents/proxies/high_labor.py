"""Proxy: expanded mixed farm with deliberately aggressive hiring."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "mixed",
    "mixed_pattern": ("MELON", "MELON", "WHEAT", "STRAWBERRY", "CARROT"),
    "base_plots": 20, "plots_per_land": 20, "max_plots": 60,
    "fixed_hands": 8, "forced_land_days": (0, 11), "selling": "immediate",
})
