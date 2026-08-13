"""C8 baseline plus a controlled second land purchase (third quadrant total)."""

from runpy import run_path


namespace = run_path("agents/replay_meta_common.py")
agent = namespace["make_replay_agent"]({
    # Preserve the C8 opening, crops, animal timing, and eight-hand ceiling.
    "animal_count": 8,
    "animal_start_day": 12,
    "structure_start_day": 11,
    "animal_workers": 4,
    "land_policy": "fixed",
    "land_purchase_days": (11, 15),
    "max_land_purchases": 2,
    "land_plots_per_quadrant": 12,
    "new_land_allocation": "adaptive",
    "land_labor_mode": "staged",
    "land_plots_per_added_hand": 2,
    "max_hands": 8,
})

