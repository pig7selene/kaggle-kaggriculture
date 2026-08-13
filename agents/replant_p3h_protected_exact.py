"""P3h: exact chain for crop workers only, vetoed by any hard deadline."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="protected_exact_chain",
)
