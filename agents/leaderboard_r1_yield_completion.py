"""R1: preserve crop capital by watering destructive crops before peak harvest."""

from runpy import run_path


agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    config={"capital_yield_completion": True},
)
