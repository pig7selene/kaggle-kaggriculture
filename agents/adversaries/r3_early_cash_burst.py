"""R3-tail adversary: early full-yield melon cash burst into crop scaling."""

from runpy import run_path


agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    cows=8,
    phase="capital_window",
    config={"capital_yield_completion": True, "value_scheduler": True},
)
