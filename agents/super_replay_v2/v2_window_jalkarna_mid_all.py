"""Elite-supported bounded market-window route replacement."""

from runpy import run_path

agent = run_path("agents/super_replay_v2/backbone_common.py")["make_agent"]('window_jalkarna_mid_all')
