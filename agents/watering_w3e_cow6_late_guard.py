"""W3e: six cows; harvest-first, then safe watering after hour 16."""

from runpy import run_path

agent = run_path("agents/predictive_watering_common.py")["make_watering"](
    cows=6, late_guard=16,
)
