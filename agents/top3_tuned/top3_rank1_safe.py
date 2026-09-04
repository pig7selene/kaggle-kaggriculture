"""Current Rank-1 public medoid with the frozen narrow livestock deadline guard."""

from runpy import run_path

agent = run_path("agents/top50_distilled/safety_common.py")["make_safe"](
    "agents/top3_tuned/raw_rank1_tetsuya.py"
)
