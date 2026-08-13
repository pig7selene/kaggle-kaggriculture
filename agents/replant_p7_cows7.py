"""P7: forecasted global seed reserve with seven cows."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="seed_reserve", cows=7,
)
