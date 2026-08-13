"""P6: forecasted global seed reserve with six cows."""

from runpy import run_path

agent = run_path("agents/replant_pipeline_common.py")["make_pipeline"](
    pipeline="seed_reserve", cows=6,
)
