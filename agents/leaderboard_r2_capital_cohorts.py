"""R2: timed day-10 melon conversion into the public second crop cohort."""

from runpy import run_path


agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    phase="capital_window",
    config={"capital_yield_completion": True},
)
