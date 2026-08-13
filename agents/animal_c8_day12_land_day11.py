"""Eight day-12 cows plus one day-11 quadrant and eight-hand crop capacity.

Selected by the disjoint-seed early-compounding search.  The historical
day-14/four-cow agent and its shared engine remain unchanged.
"""

from runpy import run_path


namespace = run_path("agents/early_compound_common.py")
config = dict(namespace["FROZEN_DAY14_CONFIG"])
config.update({
    "animal_count": 8,
    "animal_start_day": 12,
    "animal_schedule": ((12, 8),),
    "structure_start_day": 11,
    "animal_workers": 4,
    "land_policy": "fixed",
    "land_purchase_days": (11,),
    "max_land_purchases": 1,
    "land_plots_per_quadrant": 12,
    "new_land_allocation": "adaptive",
    "land_labor_mode": "staged",
    "land_plots_per_added_hand": 2,
    "max_hands": 8,
    "semantic_validation": False,
})
agent = namespace["make_agent"](config)

