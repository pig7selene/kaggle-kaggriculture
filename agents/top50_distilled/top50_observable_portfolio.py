"""Adaptive Top-50 distillation using only the opponent's visible step-1 state.

All three parent routes pass at step 0 and diverge at step 1, so the selection
does not splice incompatible states.  No seed, replay identity, rank, future
shops/prices/actions, or final result is used.
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
telemetry = {}
selected_name = None


def _select(obs):
    other = obs["farms"][1 - obs["player"]]
    money = float(other["money"])
    hands = len(other.get("hands", []))
    if money >= 2500 and hands == 0:
        return "redblack"
    if money >= 1500 and hands >= 6:
        return "hanserong"
    if 3 < money <= 10 and hands >= 5:
        return "hanserong"
    return "dmitry"


def agent(obs):
    global selected_name
    step = int(obs.get("step", 0))
    if step == 0:
        selected_name = None
        # Warm/reset all parents.  Their step-0 action is identically PASS.
        outputs = {name: parent(obs) for name, parent in PARENTS.items()}
        output = outputs["dmitry"]
    else:
        if selected_name is None:
            selected_name = _select(obs)
        output = PARENTS[selected_name](obs)
    source = PARENTS[selected_name or "dmitry"].telemetry
    telemetry.clear()
    telemetry.update(deepcopy(source))
    telemetry["portfolio_parent"] = selected_name or "pending"
    telemetry["selector_step"] = 1
    return output


agent.telemetry = telemetry
agent.parents = PARENTS
agent.feature_policy = "visible opponent money and hand count at step 1 only"
