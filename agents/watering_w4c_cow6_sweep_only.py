"""W4c: six cows and local water-task value/cohort ordering only."""

from runpy import run_path

agent = run_path("agents/predictive_watering_common.py")["make_watering"](
    cows=6, sweep=True,
)
