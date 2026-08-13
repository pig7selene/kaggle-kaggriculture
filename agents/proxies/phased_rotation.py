"""Proxy: replay-inspired melon opening followed by late wheat."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "phased", "phase_schedule": ((0, "MELON"), (21, "WHEAT")),
    "base_plots": 18, "max_plots": 18, "fixed_hands": 1,
    "selling": "aware", "liquidation_step": 600,
})
