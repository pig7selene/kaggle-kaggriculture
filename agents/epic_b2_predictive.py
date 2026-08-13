"""B2: bounded late-day crop pre-positioning only."""

from runpy import run_path

agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    config={"predictive_positioning": True, "predictive_start_hour": 18},
)
