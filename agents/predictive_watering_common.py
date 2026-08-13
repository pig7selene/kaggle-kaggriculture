"""Controlled predictive-watering candidates on isolated frozen copies."""

from runpy import run_path


COMMON = run_path("agents/epic_candidate_common.py")


def make_watering(
    *, cows, predictive=False, sweep=False, local_borrow=False,
    protect_harvest=False, deadline=False, late_guard=None,
):
    config = {}
    if predictive:
        config.update({
            "water_policy": "predictive_debt",
            "predictive_water_capacity_per_worker": 5.0,
            "predictive_water_harvest_cost": 1.0,
            "predictive_water_priority": 1.75,
            "predictive_water_value_order": True,
        })
    if sweep:
        config.update({
            "watering_sweep": True,
            "watering_sweep_radius": 2,
            "watering_sweep_weight": 25.0,
        })
    if local_borrow:
        config.update({
            "watering_local_borrow": True,
            "watering_borrow_start_hour": 16,
            "watering_borrow_max_distance": 4,
            "watering_borrow_priority": 0.9,
            "predictive_water_value_order": True,
            "watering_borrow_protect_harvest": protect_harvest,
            "watering_borrow_safe": not protect_harvest,
        })
    if deadline:
        config["water_policy"] = "deadline"
    if late_guard is not None:
        config["late_water_priority_hour"] = int(late_guard)
    return COMMON["make_candidate"](cows=cows, config=config)
