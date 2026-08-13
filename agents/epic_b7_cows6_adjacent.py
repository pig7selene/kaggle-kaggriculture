"""B7b: six-cow capacity plus bounded adjacent-territory help."""

from runpy import run_path

agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    cows=6,
    config={
        "adjacent_help": True,
        "adjacent_help_max_priority": 0.75,
        "adjacent_help_max_distance": 4,
    },
)
