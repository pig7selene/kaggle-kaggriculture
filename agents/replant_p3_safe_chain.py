"""P3 workload-admitted same-tile destructive-harvest replant chain."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="chain",
)
