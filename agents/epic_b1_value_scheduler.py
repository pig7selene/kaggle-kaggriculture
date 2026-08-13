"""B1: empirical action-value/deadline task ordering only."""

from runpy import run_path

agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    config={"value_scheduler": True},
)
