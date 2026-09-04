"""Rank-1 current-version public medoid reconstruction; not hidden source code."""

from runpy import run_path

agent = run_path("agents/top3_tuned/backbone_common.py")["make_agent"]("top3_rank1_raw")
