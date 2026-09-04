"""Ablation A+B: two narrow Top-3-evidenced Rank-1 parent substitutions."""

from runpy import run_path

agent = run_path("agents/top3_tuned/portfolio_common.py")["make_portfolio"](
    rank3_opening_swap=True,
    k3_opening_swap=True,
)
