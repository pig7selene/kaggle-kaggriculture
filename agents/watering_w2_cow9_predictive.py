"""W2: frozen nine-cow economy with debt-aware predictive watering."""

from runpy import run_path

agent = run_path("agents/predictive_watering_common.py")["make_watering"](
    cows=9, predictive=True,
)
