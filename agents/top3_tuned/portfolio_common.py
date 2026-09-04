"""Minimal Top-3-informed parent substitution in the frozen observable portfolio."""

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]


def make_portfolio(*, rank3_opening_swap=False, k3_opening_swap=False):
    parents = {
        "dmitry": run_path(str(ROOT / "agents/top50_distilled/top50_dmitry_safe.py"))["agent"],
        "hanserong": run_path(str(ROOT / "agents/top50_distilled/top50_hanserong_safe.py"))["agent"],
        "redblack": run_path(str(ROOT / "agents/top50_distilled/top50_redblack_safe.py"))["agent"],
        "rank1_safe": run_path(str(ROOT / "agents/top3_tuned/top3_rank1_safe.py"))["agent"],
    }
    telemetry = {}
    selected_name = None

    def select(obs):
        other = obs["farms"][1 - obs["player"]]
        money = float(other["money"])
        hands = len(other.get("hands", []))
        if money >= 2500 and hands == 0:
            return "rank1_safe" if rank3_opening_swap else "redblack"
        if money >= 1500 and hands >= 6:
            return "hanserong"
        if 3 < money <= 10 and hands >= 5:
            return "hanserong"
        if k3_opening_swap and money <= 3 and hands == 4:
            return "rank1_safe"
        return "dmitry"

    def agent(obs):
        nonlocal selected_name
        step = int(obs.get("step", 0))
        if step == 0:
            selected_name = None
            outputs = {name: parent(obs) for name, parent in parents.items()}
            output = outputs["dmitry"]
        else:
            if selected_name is None:
                selected_name = select(obs)
            output = parents[selected_name](obs)
        source = parents[selected_name or "dmitry"].telemetry
        telemetry.clear()
        telemetry.update(deepcopy(source))
        telemetry["portfolio_parent"] = selected_name or "pending"
        telemetry["selector_step"] = 1
        telemetry["top3_rank3_opening_swap"] = rank3_opening_swap
        telemetry["top3_k3_opening_swap"] = k3_opening_swap
        return output

    agent.telemetry = telemetry
    agent.parents = parents
    agent.feature_policy = "frozen step-1 money/hands selector plus only evidence-backed exact opening signatures"
    return agent
