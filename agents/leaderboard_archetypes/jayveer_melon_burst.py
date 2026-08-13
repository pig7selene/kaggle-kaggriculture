"""Jayveer: 42-melon day-11 capital burst into land and six cows."""

from runpy import run_path

common = run_path("agents/leaderboard_trace_common.py")
agent = common["make_trace_agent"](
    "experiments/leaderboard_replays/submission_55435253/replays/episode-92008833-replay.json", 0
)
