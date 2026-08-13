"""B3: urgent adjacent-territory assistance only."""

from runpy import run_path

agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    config={
        "adjacent_help": True,
        "adjacent_help_max_priority": 0.75,
        "adjacent_help_max_distance": 4,
    },
)
