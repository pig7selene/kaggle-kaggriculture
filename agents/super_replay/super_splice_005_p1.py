"""Compatible elite route phase splice + frozen K3 weed repair."""

from runpy import run_path

agent = run_path("agents/super_replay/super_backbone_common.py")["make_super_agent"]('super_splice_005_p1')
