"""Frozen lifecycle scheduler with seven cows; no pipeline mechanism."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](cows=7)
