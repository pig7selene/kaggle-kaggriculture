"""W3d: six cows with strict deadline/bonus-window watering."""

from runpy import run_path

agent = run_path("agents/predictive_watering_common.py")["make_watering"](
    cows=6, deadline=True,
)
