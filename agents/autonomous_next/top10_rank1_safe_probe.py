from runpy import run_path
agent = run_path("agents/top50_distilled/safety_common.py")["make_safe"]("agents/super_replay_v3/v3_raw_55425101.py")
