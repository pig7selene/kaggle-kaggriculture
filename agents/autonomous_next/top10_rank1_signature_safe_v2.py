"""Safety-gated variant of the Top-10 Rank-1 signature probe.

The route selection is identical to ``top10_rank1_signature_v1``; only the
existing bounded feed-deadline repair wraps the complete Rank-1 route.
"""

from copy import deepcopy
from pathlib import Path
from runpy import run_path

ROOT = Path(__file__).resolve().parents[2]
BASE = run_path(str(ROOT / "agents/top50_distilled/top50_observable_portfolio.py"))["agent"]
RANK1 = run_path(str(ROOT / "agents/top50_distilled/safety_common.py"))["make_safe"](
    "agents/super_replay_v3/v3_raw_55425101.py"
)
telemetry = {}
_state = {"last_step": -1, "selected": None}


def _reset():
    _state.clear(); _state.update({"last_step": -1, "selected": None})
    telemetry.clear(); telemetry.update({"calls": 0, "selected": None, "rank1_eligible": False})


def _eligible(obs):
    if int(obs.get("step", 0)) != 1:
        return False
    other = obs["farms"][1 - obs["player"]]
    pastures = sum(
        isinstance(tile, dict) and tile.get("kind") == "PASTURE"
        for row in other.get("tiles", []) for tile in row
    )
    return len(other.get("hands", [])) == 5 and pastures >= 1 and 0.0 < float(other.get("money", 0.0)) <= 120.0


def agent(obs):
    step = int(obs.get("step", 0))
    if not _state or step == 0 or step <= int(_state.get("last_step", -1)):
        _reset()
    _state["last_step"] = step
    telemetry["calls"] = int(telemetry.get("calls", 0)) + 1
    base_action = BASE(obs)
    rank1_action = RANK1(obs)
    if _state["selected"] is None and step >= 1:
        _state["selected"] = "rank1" if _eligible(obs) else "portfolio"
        telemetry["rank1_eligible"] = _state["selected"] == "rank1"
    if _state["selected"] == "rank1":
        output, source = rank1_action, getattr(RANK1, "telemetry", {}) or {}
    else:
        output, source = base_action, getattr(BASE, "telemetry", {}) or {}
    for key in ("all_route_matches", "all_route_requests", "repair_abort", "fallback_step"):
        telemetry[key] = source.get(key, 0 if key.endswith("matches") or key.endswith("requests") else None)
    telemetry["repairs"] = deepcopy(source.get("repairs", {"weed": 0}))
    telemetry["selected"] = _state["selected"] or "pending"
    telemetry["portfolio_parent"] = _state["selected"] or "pending"
    return deepcopy(output)


agent.telemetry = telemetry
agent.base = BASE
agent.rank1 = RANK1
agent.description = "Top-10 Rank-1 signature branch with bounded feed safety repair"
