from runpy import run_path
agent = run_path("agents/super_replay_v4/common.py")["make_agent"](module="E", endgame="liquidate_from_day27")
