"""B7e: six-cow capacity plus the corrected replay crop phase."""

from runpy import run_path

agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    cows=6,
    phase="replay_phase",
)
