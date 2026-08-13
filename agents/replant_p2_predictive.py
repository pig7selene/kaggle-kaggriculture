"""P2 short-horizon imminent destructive-harvest positioning."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="predictive",
)
