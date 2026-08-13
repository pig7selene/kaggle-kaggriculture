"""V2 elite route with frozen bounded K3 worker weed repair."""

from runpy import run_path

agent = run_path("agents/super_replay_v2/backbone_common.py")["make_agent"]('super_raw_55455766')
