"""Complete-route state owner (control).

This module is intentionally action-equivalent to the frozen observable
portfolio.  It adds an explicit commitment ledger from turn zero so later
experiments can reserve worker/crop capacity without splicing an unrelated
route into an already evolved farm state.
"""

from copy import deepcopy
from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
BASE = run_path(str(ROOT / "agents/top50_distilled/top50_observable_portfolio.py"))["agent"]

state = {}
telemetry = {}


def _reset(obs):
    state.clear()
    state.update({
        "last_step": int(obs.get("step", 0)) - 1,
        "reserved_worker": 0,
        "reserved_crop": "WHEAT",
        "reservation_start": 240,
        "reservation_end": 600,
        "ledger": {},
    })
    telemetry.clear()
    telemetry.update({
        "calls": 0,
        "reservation_planned_at": 0,
        "reserved_worker": 0,
        "reserved_crop": "WHEAT",
        "base_actions": 0,
        "base_market_orders": 0,
        "ledger_updates": 0,
    })


def _op(action):
    return action[0] if isinstance(action, list) and action else "PASS"


def _record(obs, action):
    farm = obs["farms"][obs["player"]]
    units = [action.get("farmer", ["PASS"]), *list(action.get("hands", []))]
    ledger = state.setdefault("ledger", {})
    for index, unit_action in enumerate(units):
        op = _op(unit_action)
        record = ledger.setdefault(str(index), {"calls": 0, "ops": {}})
        record["calls"] += 1
        record["ops"][op] = int(record["ops"].get(op, 0)) + 1
    telemetry["base_actions"] += len(units)
    telemetry["base_market_orders"] += len(action.get("market", []))
    telemetry["ledger_updates"] += 1
    telemetry["last_day"] = int(obs.get("day", 0))
    telemetry["last_hands"] = len(farm.get("hands", []))


def agent(obs):
    step = int(obs.get("step", 0))
    if not state or step == 0 or step <= int(state.get("last_step", -1)):
        _reset(obs)
    state["last_step"] = step
    telemetry["calls"] += 1
    action = deepcopy(BASE(obs))
    # The reservation exists before the opening route has created any hands;
    # this is the key distinction from a post-checkpoint overlay.  The control
    # does not consume that reservation, so its output remains byte-for-byte
    # equal to BASE.
    _record(obs, action)
    return action


agent.telemetry = telemetry
agent.description = "action-equivalent complete-route owner with day-0 worker/crop reservation ledger"
agent.base = BASE
