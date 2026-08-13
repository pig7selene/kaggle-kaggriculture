"""P3d: five-turn explicit harvested-tile queue with watering veto."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="pending_chain",
)
