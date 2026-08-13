"""One evidence-backed branch: V2 or compatible Furious-Monk tail at step 160."""

from runpy import run_path


_make_v2 = run_path("submission/main.py")["make_v27_agent"]
_make_tail = run_path("agents/super_replay_v3/v3_tail_55474695_160.py")["make_v27_agent"]
_v2 = _make_v2()
_tail = _make_tail()
_selected = None


def agent(obs):
    global _selected
    if int(obs.get("step", 0)) == 0:
        _selected = None
    action_v2 = _v2(obs)
    action_tail = _tail(obs)
    if int(obs["step"]) == 160 and _selected is None:
        opponent_money = float(obs["farms"][1 - int(obs["player"])]["money"])
        _selected = "tail" if opponent_money <= 644 else "v2"
    chosen = _tail if _selected == "tail" else _v2
    output = action_tail if _selected == "tail" else action_v2
    agent.telemetry = chosen.telemetry
    agent.route = chosen.route
    agent.branch_choice = _selected
    return output


agent.telemetry = _v2.telemetry
agent.route = _v2.route
agent.stage = 3
agent.stage_name = "K3_weed_transaction_repair"
agent.branch_choice = None
