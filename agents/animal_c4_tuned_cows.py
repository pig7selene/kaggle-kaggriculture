"""C4: search-selected early four-cow policy on phased crops."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "phased", "phase_schedule": ((0, "MELON"), (11, "STRAWBERRY"), (21, "WHEAT")),
    "selling": "immediate", "animal_type": "COW", "animal_count": 4,
    "animal_start_day": 0, "structure_start_day": 0, "animal_region": "NW",
    "animal_clear_weeds": True, "require_animal_payback": True,
    "animal_workers": 2, "animal_survival_priority": True,
    "feed_policy": "daily", "care_policy": "daily",
    "fertilizer_policy": "collect", "animal_harvest_threshold": 1,
    "wheat_policy": "market", "wheat_reserve_days": 2,
    "liquidate_feed_reserve": True,
    "animal_selling": "aware", "animal_sell_threshold": 1.10,
    "animal_premium_sell_threshold": 1.10, "animal_hold_days": 2,
    "animal_endgame_priority": True, "endgame_return_hour": 12,
})
