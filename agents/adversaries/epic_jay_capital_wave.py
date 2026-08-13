"""Hard replay-derived adversary: contiguous melon wave into crop scaling."""

from runpy import run_path

agent = run_path("agents/epic_candidate_common.py")["make_candidate"](
    cows=8,
    phase="replay_phase",
)
