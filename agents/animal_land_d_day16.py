"""D: C2 plus one ROI-gated quadrant scheduled for day 16."""

from runpy import run_path

namespace = run_path("agents/animal_land_common.py")
config = dict(namespace["C2_LAND_BASE"])
config.update({"max_land_purchases": 1, "land_purchase_days": (16,)})
agent = namespace["make_agent"](config)
