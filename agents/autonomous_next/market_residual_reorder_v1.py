"""Market-only residual over the frozen Top-50 observable portfolio.

The underlying route and every non-SELL action are left untouched.  When a
route emits multiple SELL orders in one turn, the bounded exact own-market
simulation from the replay backbone chooses the best permutation of those
existing SELL slots.  No order is added, removed, or moved across turns.
"""

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
BASE = run_path(str(ROOT / "agents/top50_distilled/top50_observable_portfolio.py"))["agent"]
COMMON = run_path(str(ROOT / "agents/v27_backbone_common.py"))
REORDER = COMMON["_reorder_current_sells"]

telemetry = {
    "calls": 0,
    "reorder_calls": 0,
    "reordered_turns": 0,
    "estimated_original_revenue": 0.0,
    "estimated_optimized_revenue": 0.0,
}


def _reset():
    telemetry.clear()
    telemetry.update({
        "calls": 0,
        "reorder_calls": 0,
        "reordered_turns": 0,
        "estimated_original_revenue": 0.0,
        "estimated_optimized_revenue": 0.0,
    })


def agent(obs):
    if int(obs.get("step", 0)) == 0:
        _reset()
    telemetry["calls"] += 1
    action = deepcopy(BASE(obs))
    market = action.get("market", [])
    sell_count = sum(1 for order in market if order and order[0] == "SELL")
    if sell_count >= 2:
        telemetry["reorder_calls"] += 1
        try:
            reordered, original, optimized = REORDER(obs, market)
            telemetry["estimated_original_revenue"] += float(original.get("sell_revenue", 0.0))
            telemetry["estimated_optimized_revenue"] += float(optimized.get("sell_revenue", 0.0))
            if reordered != market:
                telemetry["reordered_turns"] += 1
            action["market"] = reordered
        except Exception:
            # A residual optimizer must never interfere with the frozen route.
            action["market"] = market
    return action


agent.telemetry = telemetry
agent.base = BASE
agent.policy = "existing SELL slots only; bounded exact own-market permutation"
