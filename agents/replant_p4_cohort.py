"""P4 bounded local destructive-harvest cohort sweep."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="cohort",
)
