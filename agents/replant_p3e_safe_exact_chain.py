"""P3e: exact same-worker harvest chain gated by territory workload slack."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="safe_exact_chain",
)
