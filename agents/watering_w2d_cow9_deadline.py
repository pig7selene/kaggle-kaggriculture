"""W2d: frozen nine-cow economy with strict deadline/bonus watering."""

from runpy import run_path

agent = run_path("agents/predictive_watering_common.py")["make_watering"](
    cows=9, deadline=True,
)
