"""B5: replay-derived crop allocation and transition days only."""

from runpy import run_path

agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    phase="replay_phase",
)
