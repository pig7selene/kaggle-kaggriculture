"""Isolated endgame-milk ablation around the frozen routed replay agent.

Only empty-handed animal specialists receive two additional hours (16 and 17)
to collect already-produced animal output on day 29.  The original inventory
return rule, selling logic, crop logic, economy, and router are unchanged.
"""

from copy import deepcopy
from runpy import run_path


namespace = run_path("agents/router_replay_hands12.py")
agent = namespace["agent"]
router_globals = agent.__globals__
original_animal_action = router_globals["_animal_action"]


def _late_animal_action(obs, *args, **kwargs):
    if obs["day"] == 29 and 15 < obs["hour"] <= 17:
        planning_obs = deepcopy(obs)
        planning_obs["hour"] = 15
        return original_animal_action(planning_obs, *args, **kwargs)
    return original_animal_action(obs, *args, **kwargs)


router_globals["_animal_action"] = _late_animal_action

