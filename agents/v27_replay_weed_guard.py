"""Promoted research candidate: stable Victor V27 route + bounded weed repair."""

from runpy import run_path

agent = run_path("agents/v27_backbone_common.py")["make_v27_agent"](stage=3)
