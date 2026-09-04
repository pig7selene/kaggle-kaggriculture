"""Top-10-informed complete-parent selector.

The frozen Top-50 observable portfolio remains the default economy.  A stable,
previously safety-clean Top-10 JALKARNA route is admitted only when the visible
step-1 opening is its characteristic low-bank/four-hand state.  Both routes
are warmed from step 0 and the choice is made once, before any incompatible
state can be spliced.  No later switching or action overlay is performed.
"""

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
BASE = run_path(str(ROOT / "agents/top50_distilled/top50_observable_portfolio.py"))["agent"]
JALKARNA = run_path(str(ROOT / "agents/super_replay_v3/v3_raw_55463387.py"))["agent"]

telemetry = {}
state = {}


def _reset():
    state.clear()
    state.update({"last_step": -1, "selected": None, "selection_step": None})
    telemetry.clear()
    telemetry.update({"calls": 0, "selected": None, "selection_step": None, "jalkarna_eligible": False})


def _eligible(obs):
    """Top-10 JALKARNA opening signature visible after its step-0 commit."""
    other = obs["farms"][1 - obs["player"]]
    money = float(other.get("money", 0.0))
    hands = len(other.get("hands", []))
    # The route's public step-1 state is three coins and four hands.  Keep a
    # small bank tolerance for server rounding, but do not match ordinary
    # Top-50 PASS openings (3,000 coins and zero hands).
    return money <= 10.0 and 4 <= hands <= 5


def agent(obs):
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)):
        _reset()
    state["last_step"] = step
    telemetry["calls"] += 1

    # Warm both complete executors on every observation so either route owns a
    # coherent internal state if it is selected at the single branch point.
    base_action = BASE(obs)
    jalkarna_action = JALKARNA(obs)

    if state["selected"] is None and step >= 1:
        if _eligible(obs):
            state["selected"] = "jalkarna"
            telemetry["jalkarna_eligible"] = True
        else:
            state["selected"] = "portfolio"
        state["selection_step"] = step
        telemetry["selected"] = state["selected"]
        telemetry["selection_step"] = step

    if state["selected"] == "jalkarna":
        output = jalkarna_action
        source_telemetry = getattr(JALKARNA, "telemetry", {}) or {}
    elif state["selected"] == "portfolio":
        output = base_action
        source_telemetry = getattr(BASE, "telemetry", {}) or {}
    else:
        # Both routes have a documented PASS warm-up at step 0.
        output = base_action
        source_telemetry = getattr(BASE, "telemetry", {}) or {}
    # The common league auditor expects the normal route telemetry shape.  Keep
    # our selector fields while forwarding route-fidelity/safety counters from
    # whichever complete parent is live.
    for key in ("all_route_matches", "all_route_requests", "repair_abort", "fallback_step"):
        telemetry[key] = source_telemetry.get(key, 0 if key.endswith("matches") or key.endswith("requests") else None)
    telemetry["repairs"] = deepcopy(source_telemetry.get("repairs", {"weed": 0}))
    telemetry["selected"] = state["selected"] or "pending"
    return deepcopy(output)


agent.telemetry = telemetry
agent.base = BASE
agent.jalkarna = JALKARNA
agent.description = "Top-10 stable JALKARNA complete parent selected on exact step-1 low-bank/four-hand signature"
