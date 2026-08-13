"""Alexander: cow-funded land followed by synchronized melon realization."""

from runpy import run_path

common = run_path("agents/leaderboard_trace_common.py")
agent = common["make_trace_agent"](
    "experiments/leaderboard_replays/submission_55435253/replays/episode-92011750-replay.json", 0
)
