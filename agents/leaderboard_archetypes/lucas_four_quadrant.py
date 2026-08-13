"""Lucas: large melon wave into a four-quadrant crop/livestock economy."""

from runpy import run_path

common = run_path("agents/leaderboard_trace_common.py")
agent = common["make_trace_agent"](
    "experiments/leaderboard_replays/submission_55435253/replays/episode-92009080-replay.json", 1
)
