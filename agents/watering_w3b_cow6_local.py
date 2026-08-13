"""W3b: six cows with bounded same-quadrant deadline prevention."""

from runpy import run_path

agent = run_path("agents/predictive_watering_common.py")["make_watering"](
    cows=6, local_borrow=True,
)
