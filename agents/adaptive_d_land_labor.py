"""Ablation D: pure melons with ROI-gated land and workload-based labor."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "fixed",
    "fixed_crop": "MELON",
    "selling": "immediate",
    "enable_land": True,
    "dynamic_labor": True,
})
