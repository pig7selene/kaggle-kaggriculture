"""W4b: W3b plus value-weighted local watering cluster preference."""

from runpy import run_path

agent = run_path("agents/predictive_watering_common.py")["make_watering"](
    cows=6, local_borrow=True, sweep=True,
)
