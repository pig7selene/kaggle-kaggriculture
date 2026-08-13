"""R3-tail adversary: high-scale crop throughput with a light animal claim."""

from runpy import run_path


agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    cows=6,
    phase="capital_window",
    config={"capital_yield_completion": True, "value_scheduler": True},
)
