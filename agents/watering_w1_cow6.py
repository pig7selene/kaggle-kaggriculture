"""W1: clean frozen architecture with only the herd target reduced to six."""

from runpy import run_path

agent = run_path("agents/predictive_watering_common.py")["make_watering"](cows=6)
