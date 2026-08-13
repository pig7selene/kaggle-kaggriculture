"""F: C2 plus one quadrant after the measured cow payback window."""

from runpy import run_path

namespace = run_path("agents/animal_land_common.py")
config = dict(namespace["C2_LAND_BASE"])
config.update({
    "land_policy": "cow_payback",
    "max_land_purchases": 1,
    "land_cow_payback_day": 20,
})
agent = namespace["make_agent"](config)
