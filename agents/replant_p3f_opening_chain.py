"""P3f: preserve the frozen router's stationary replant on day 10."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="opening_chain",
)
