"""Hard replay-derived adversary: crop economy plus bounded wheat demand capture."""

from runpy import run_path

common = run_path("agents/epic_candidate_common.py")
base = common["make_candidate"](cows=8, phase="replay_phase")
agent = common["demand_capture_wrapper"](base, units=16, cash_reserve=1200)
