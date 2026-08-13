"""G: C2 plus bank- and ROI-gated dynamic single-quadrant expansion."""

from runpy import run_path

namespace = run_path("agents/animal_land_common.py")
config = dict(namespace["C2_LAND_BASE"])
config.update({
    "land_policy": "dynamic_roi",
    "max_land_purchases": 1,
    "land_min_day": 11,
    "land_bank_thresholds": (9000,),
    "land_roi_hurdle": 0.10,
})
agent = namespace["make_agent"](config)
