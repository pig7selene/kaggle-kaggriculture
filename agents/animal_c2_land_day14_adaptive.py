"""C2 cows plus one day-14 ROI-gated quadrant with adaptive crops."""

from runpy import run_path

namespace = run_path("agents/animal_land_common.py")
config = dict(namespace["C2_LAND_BASE"])
config.update({
    "land_policy": "fixed",
    "land_purchase_days": (14,),
    "max_land_purchases": 1,
    "land_roi_hurdle": 0.0,
    "land_plots_per_quadrant": 12,
    "new_land_allocation": "adaptive",
    "land_labor_mode": "staged",
    "land_plots_per_added_hand": 4,
    "max_hands": 8,
})
agent = namespace["make_agent"](config)
