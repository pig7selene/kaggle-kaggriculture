"""W4: six-cow predictive watering with bounded local cluster preference."""

from runpy import run_path

agent = run_path("agents/predictive_watering_common.py")["make_watering"](
    cows=6, predictive=True, sweep=True,
)
