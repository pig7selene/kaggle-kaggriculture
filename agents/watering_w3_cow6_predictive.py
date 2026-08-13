"""W3: six cows plus debt-aware predictive watering."""

from runpy import run_path

agent = run_path("agents/predictive_watering_common.py")["make_watering"](
    cows=6, predictive=True,
)
