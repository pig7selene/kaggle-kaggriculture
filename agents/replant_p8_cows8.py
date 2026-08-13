"""P8: forecasted global seed reserve with eight cows."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="seed_reserve", cows=8,
)
