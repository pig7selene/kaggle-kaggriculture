"""Ablation F: adaptive crops/selling plus dynamic land and labor."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "adaptive",
    "selling": "aware",
    "enable_land": True,
    "dynamic_labor": True,
})
