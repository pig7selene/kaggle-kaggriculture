"""Proxy: premium melon inventory holder with late liquidation."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "fixed", "fixed_crop": "MELON", "base_plots": 16,
    "max_plots": 16, "fixed_hands": 2, "selling": "aware",
    "premium_sell_threshold": 1.10, "forecast_sell_ratio": 1.05,
    "overflow_trigger": 90, "reserve_level": 70, "liquidation_step": 576,
})
