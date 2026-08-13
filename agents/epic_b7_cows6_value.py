"""B7a: six-cow capacity plus the isolated action-value scheduler."""

from runpy import run_path

agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    cows=6,
    config={"value_scheduler": True},
)
