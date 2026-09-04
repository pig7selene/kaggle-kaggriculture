"""Conservative Top-10-informed selector adjustment.

Top-10 mining found a recurring low-bank/four-hand opening family, but the
raw JALKARNA route is not safe as a universal transfer.  This candidate keeps
the frozen Top-50 complete parents and only routes that signature to the
already safety-repaired Hanserong (7-cow/6-sheep) parent.  The choice is made
once at step 1; no route is spliced later.
"""

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
PARENTS = {
    "dmitry": run_path(str(ROOT / "agents/top50_distilled/top50_dmitry_safe.py"))["agent"],
    "hanserong": run_path(str(ROOT / "agents/top50_distilled/top50_hanserong_safe.py"))["agent"],
    "redblack": run_path(str(ROOT / "agents/top50_distilled/top50_redblack_safe.py"))["agent"],
}
state = {}
telemetry = {}


def _reset():
    state.clear()
    state.update({"last_step": -1, "selected": None, "selection_step": None, "lowbank_match": False})
    telemetry.clear()
    telemetry.update({"calls": 0, "selected": None, "selection_step": None, "lowbank_match": False})


def _select(obs):
    other = obs["farms"][1 - obs["player"]]
    money = float(other.get("money", 0.0))
    hands = len(other.get("hands", []))
    if money <= 10.0 and 4 <= hands <= 5:
        state["lowbank_match"] = True
        return "hanserong"
    if money >= 2500.0 and hands == 0:
        return "redblack"
    if money >= 1500.0 and hands >= 6:
        return "hanserong"
    if 3.0 < money <= 10.0 and hands >= 5:
        return "hanserong"
    return "dmitry"


def _sync(source):
    source = getattr(source, "telemetry", {}) or {}
    for key in ("all_route_matches", "all_route_requests", "repair_abort", "fallback_step"):
        telemetry[key] = source.get(key, 0 if key.endswith(("matches", "requests")) else None)
    telemetry["repairs"] = deepcopy(source.get("repairs", {"weed": 0}))


def agent(obs):
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)):
        _reset()
    state["last_step"] = step
    telemetry["calls"] += 1

    if step == 0:
        # Warm all complete parents. Their step-0 action is identical.
        outputs = {name: parent(obs) for name, parent in PARENTS.items()}
        output = outputs["dmitry"]
        _sync(PARENTS["dmitry"])
        telemetry["selected"] = "pending"
        return deepcopy(output)

    if state["selected"] is None:
        state["selected"] = _select(obs)
        state["selection_step"] = step
        telemetry["selection_step"] = step
    selected = state["selected"]
    output = PARENTS[selected](obs)
    _sync(PARENTS[selected])
    telemetry["selected"] = selected
    telemetry["portfolio_parent"] = selected
    telemetry["lowbank_match"] = bool(state["lowbank_match"])
    return deepcopy(output)


agent.telemetry = telemetry
agent.parents = PARENTS
agent.description = "Top-10 low-bank/four-hand signature -> proven Hanserong parent; otherwise frozen selector"
