"""Frozen lifecycle scheduler with six cows; no pipeline mechanism."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](cows=6)
