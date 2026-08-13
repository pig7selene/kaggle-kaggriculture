"""Ablation B: pure melons with inventory-aware selling."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "fixed",
    "fixed_crop": "MELON",
    "selling": "aware",
})
