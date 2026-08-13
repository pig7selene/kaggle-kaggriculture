"""W3c: six cows; borrow for critical local water only after own harvests."""

from runpy import run_path

agent = run_path("agents/predictive_watering_common.py")["make_watering"](
    cows=6, local_borrow=True, protect_harvest=True,
)
