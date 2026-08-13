"""P0 isolated control for replant-pipeline research."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"]()
