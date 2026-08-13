"""P3c: exact next-turn same-worker chain inferred from carried harvest product."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="inventory_chain",
)
