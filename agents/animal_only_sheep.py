"""Controlled animal-only experiment: four sheep with market-bought feed."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({
    "crop_mode": "phased", "phase_schedule": ((0, "MELON"), (11, "STRAWBERRY"), (21, "WHEAT")),
    "base_plots": 0, "max_plots": 8, "selling": "immediate",
    "animal_type": "SHEEP", "animal_count": 4, "animal_start_day": 0,
    "structure_start_day": 0, "animal_region": "NW", "animal_clear_weeds": True,
    "animal_workers": 2, "feed_policy": "daily", "care_policy": "daily",
    "fertilizer_policy": "collect", "wheat_policy": "market",
    "animal_selling": "aware", "liquidate_feed_reserve": True,
    "animal_endgame_priority": True,
    "endgame_return_hour": 12,
})
