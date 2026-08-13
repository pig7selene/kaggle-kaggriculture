"""Hak: high-income public fixed-template crop-throughput representative."""

from runpy import run_path

common = run_path("agents/leaderboard_trace_common.py")
agent = common["make_trace_agent"](
    "experiments/top_player_replays/replays/episode-91853240-replay.json", 1
)
