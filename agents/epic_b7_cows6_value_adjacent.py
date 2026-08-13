"""B7c: combine the two positive router ablations on six cows."""

from runpy import run_path

agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    cows=6,
    config={
        "value_scheduler": True,
        "adjacent_help": True,
        "adjacent_help_max_priority": 0.75,
        "adjacent_help_max_distance": 4,
    },
)
