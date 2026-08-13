"""Proxy: sparse-labor melon farm with replay-timed aggressive expansion."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "phased", "phase_schedule": ((0, "MELON"), (21, "WHEAT")),
    "base_plots": 20, "plots_per_land": 10, "max_plots": 40,
    "fixed_hands": 1, "forced_land_days": (0, 11, 11),
    "selling": "aware", "liquidation_step": 600,
})
