"""P5 predictive + safe chain + small local cohort pipeline."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="combined",
)
