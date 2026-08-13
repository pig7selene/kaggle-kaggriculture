"""Ablation A: adaptive crop selection with baseline selling/land/labor."""

from runpy import run_path

make_agent = run_path("agents/economic_common.py")["make_agent"]
agent = make_agent({"crop_mode": "adaptive", "selling": "immediate"})
