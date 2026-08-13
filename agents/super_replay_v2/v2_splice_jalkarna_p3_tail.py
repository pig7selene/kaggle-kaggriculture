"""Evidence-backed coherent V2 phase splice + bounded K3 weed repair."""

from runpy import run_path

agent = run_path("agents/super_replay_v2/backbone_common.py")["make_agent"]('splice_jalkarna_p3_tail')
