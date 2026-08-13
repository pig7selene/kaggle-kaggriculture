"""W0: action-equivalent frozen nine-cow control on isolated copies."""

from runpy import run_path

agent = run_path("agents/predictive_watering_common.py")["make_watering"](cows=9)
