"""P3i: exact chain for crop workers through the frozen safe hour limit."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="bounded_exact_chain",
)
