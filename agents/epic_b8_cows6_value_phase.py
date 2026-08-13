"""B8: six cows, action-value scheduling, and replay crop phasing."""

from runpy import run_path

agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    cows=6,
    phase="replay_phase",
    config={"value_scheduler": True},
)
