"""Exact public-replay action traces used as high-fidelity local opponents."""

from copy import deepcopy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def make_trace_agent(replay_path, player):
    replay = json.loads((ROOT / replay_path).read_text())
    player = int(player)

    def agent(obs):
        # Kaggle stores the requested action beside the state resulting from
        # the previous request, hence the one-step offset.
        index = min(int(obs["step"]) + 1, len(replay["steps"]) - 1)
        action = deepcopy(replay["steps"][index][player].get("action") or {})
        action.setdefault("farmer", ["PASS"])
        action.setdefault("market", [])
        hands = list(action.get("hands", []))
        required = len(obs["farms"][obs["player"]].get("hands", []))
        hands.extend([["PASS"]] * max(0, required - len(hands)))
        action["hands"] = hands[:required]
        return action

    agent.source_replay = str(replay_path)
    agent.source_player = player
    return agent
