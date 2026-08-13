"""R4: timed capital cohorts plus action-value execution at nine-cow scale."""

from runpy import run_path


agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    phase="capital_window",
    config={"capital_yield_completion": True, "value_scheduler": True},
)
