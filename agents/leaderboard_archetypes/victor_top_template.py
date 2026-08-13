"""Victor: top-public day-6/day-10 scaler with full-yield crop cohorts."""

from runpy import run_path

common = run_path("agents/leaderboard_trace_common.py")
agent = common["make_trace_agent"](
    "experiments/top_player_replays/replays/episode-91869963-replay.json", 0
)
