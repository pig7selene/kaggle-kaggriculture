"""P1 global forecasted seed reserve; workers cannot carry seeds."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="seed_reserve",
)
