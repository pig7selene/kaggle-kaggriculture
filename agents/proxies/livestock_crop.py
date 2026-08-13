"""Proxy: melon/wheat rotation with land-funded cows and held premiums."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "phased", "phase_schedule": ((0, "MELON"), (21, "WHEAT")),
    "base_plots": 18, "plots_per_land": 12, "max_plots": 30,
    "fixed_hands": 5, "forced_land_days": (11,), "selling": "aware",
    "animal_type": "COW", "animal_count": 4, "animal_start_day": 11,
})
