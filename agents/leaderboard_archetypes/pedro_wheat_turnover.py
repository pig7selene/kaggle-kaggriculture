"""Pedro: mixed crop economy with repeated two-turn wheat inventory turnover."""

from runpy import run_path

common = run_path("agents/leaderboard_trace_common.py")
agent = common["make_trace_agent"](
    "experiments/leaderboard_replays/submission_55435253/replays/episode-92010768-replay.json", 1
)
