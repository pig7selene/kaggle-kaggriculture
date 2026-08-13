"""P3g: extend the frozen non-specialist stationary chain through hour 23."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="extended_chain",
)
