"""Seven cows with the selected strict deadline/bonus watering scheduler."""

from runpy import run_path

agent = run_path("agents/predictive_watering_common.py")["make_watering"](
    cows=7, deadline=True,
)
