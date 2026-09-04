"""Top-10 Rank-1 signature probe over the frozen observable portfolio.

This is a complete-route experiment, not a mid-episode splice.  The
Top-10/Kawashigi route is selected only when the opponent's public step-1
state exposes its characteristic five-hand, one-pasture, low-bank opening.
All other observations delegate to the unchanged Top-50 observable
portfolio.  The candidate is retained for research only.
"""

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
BASE = run_path(str(ROOT / "agents/top50_distilled/top50_observable_portfolio.py"))["agent"]
RANK1 = run_path(str(ROOT / "agents/super_replay_v3/v3_raw_55425101.py"))["agent"]

telemetry = {}
_state = {"last_step": -1, "selected": None}


def _reset():
    _state.clear()
    _state.update({"last_step": -1, "selected": None})
    telemetry.clear()
    telemetry.update({"calls": 0, "selected": None, "rank1_eligible": False})


def _pastures(farm):
    return sum(
        isinstance(tile, dict) and tile.get("kind") == "PASTURE"
        for row in farm.get("tiles", []) for tile in row
    )


def _eligible(obs):
    """Public step-1 signature observed in the Rank-1 Top-10 corpus."""
    if int(obs.get("step", 0)) != 1:
        return False
    other = obs["farms"][1 - obs["player"]]
    money = float(other.get("money", 0.0))
    hands = len(other.get("hands", []))
    return hands == 5 and _pastures(other) >= 1 and 0.0 < money <= 120.0


def agent(obs):
    step = int(obs.get("step", 0))
    if not _state or step == 0 or step <= int(_state.get("last_step", -1)):
        _reset()
    _state["last_step"] = step
    telemetry["calls"] = int(telemetry.get("calls", 0)) + 1

    # Warm both complete routes.  They both pass at step 0, so no state is
    # committed before the single branch point.
    base_action = BASE(obs)
    rank1_action = RANK1(obs)
    if _state["selected"] is None and step >= 1:
        if _eligible(obs):
            _state["selected"] = "rank1"
            telemetry["rank1_eligible"] = True
        else:
            _state["selected"] = "portfolio"

    if _state["selected"] == "rank1":
        output = rank1_action
        source = getattr(RANK1, "telemetry", {}) or {}
    else:
        output = base_action
        source = getattr(BASE, "telemetry", {}) or {}

    for key in ("all_route_matches", "all_route_requests", "repair_abort", "fallback_step"):
        telemetry[key] = source.get(
            key, 0 if key.endswith("matches") or key.endswith("requests") else None
        )
    telemetry["repairs"] = deepcopy(source.get("repairs", {"weed": 0}))
    telemetry["selected"] = _state["selected"] or "pending"
    telemetry["portfolio_parent"] = _state["selected"] or "pending"
    return deepcopy(output)


agent.telemetry = telemetry
agent.base = BASE
agent.rank1 = RANK1
agent.description = "Top-10 Rank-1 complete route selected on five-hand/pasture/low-bank step-1 signature"
