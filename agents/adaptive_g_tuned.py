"""Search winner: phase-aware adaptive crops with inventory-aware selling."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "adaptive",
    "selling": "aware",
    "phased_weights": True,
})
