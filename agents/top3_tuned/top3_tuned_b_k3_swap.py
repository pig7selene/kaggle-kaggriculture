"""Ablation B: replace only the exact K3-opening branch with Rank-1."""

from runpy import run_path

agent = run_path("agents/top3_tuned/portfolio_common.py")["make_portfolio"](
    k3_opening_swap=True,
)
