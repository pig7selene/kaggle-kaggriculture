"""R6: checkpoint cash forecast controls the day-20 melon capital cohort."""

from runpy import run_path


agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    phase="capital_planner",
    config={"capital_yield_completion": True, "value_scheduler": True},
)
