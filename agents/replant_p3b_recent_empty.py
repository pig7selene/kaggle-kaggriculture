"""P3b: bounded high-priority replant of nearby active-territory empty tiles."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="recent_empty",
)
