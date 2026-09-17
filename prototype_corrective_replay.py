"""Replay a recorded trajectory by chasing its state, not by repeating its actions.

A raw tape breaks the moment anything differs: Majkel's own game replayed
against another opponent makes 4,194 instead of 116,326, because a few coins of
market difference make the step-25 hires fail and the farm never recovers.

The recording holds more than the actions. For every step it also holds the
state the agent was in: where each unit stood, how many hands it had, what was
in its seed bag and shed, which quadrants it owned. So replay the *state*:

  - units: if a unit is not where the recording had it, walk it there instead of
    performing an action it cannot perform from the wrong tile;
  - purchases: compare our hands, seeds, animals and land with the recording at
    this step and buy the difference when we can afford it, rather than
    repeating an order that already failed;
  - obstacles: dig a weed that sits where the recording wanted to plant or build.

Everything else -- what to plant, when to harvest, what to sell -- is the
recording's. This is the diagnostic version: one episode, one seed, printing how
far each layer gets.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from kaggle_environments import make

from analyze_v27_routes import normalized_action
from run_route_remap_pilot import load_agent

ROOT = Path(__file__).resolve().parent
SHIPPED = Path("/private/tmp/kaggriculture_v43_variants/shipped.py")
MOVES = {"EAST": (1, 0), "WEST": (-1, 0), "SOUTH": (0, 1), "NORTH": (0, -1)}
PRODUCTS = ("CARROT", "EGG", "FERTILIZER", "MELON", "MILK", "STRAWBERRY", "TOMATO", "WHEAT", "WOOL")
ANIMALS = ("COW", "SHEEP", "GOOSE")


def full_obs(rep, s, seat):
    o = dict(rep["steps"][s][seat]["observation"])
    for k in ("step", "day", "hour", "farms", "market", "town"):
        if k not in o:
            o[k] = rep["steps"][s][0]["observation"][k]
    return o


def extract(rep, seat):
    """Per step: unit positions, unit actions, market orders, and target counts."""
    plan = []
    for s in range(719):
        o = full_obs(rep, s, seat)
        f = o["farms"][seat]
        a = normalized_action(rep, seat, s)
        plan.append({
            "pos": [tuple(f["farmer"])] + [tuple(p) for p in f["hands"]],
            "units": [a.get("farmer") or ["PASS"]] + list(a.get("hands") or []),
            "market": [list(x) for x in (a.get("market") or []) if x],
            "hands": len(f["hands"]),
            "seeds": dict(o["private"].get("seeds", {})),
            "animals": {k: int(v) for k, v in o["private"]["shed"].items() if k in ANIMALS},
            "quadrants": len(f["unlocked_quadrants"]),
            "money": f["money"],
        })
    return plan


def step_toward(cur, tgt):
    dx, dy = tgt[0] - cur[0], tgt[1] - cur[1]
    if dx > 0:
        return ["EAST"]
    if dx < 0:
        return ["WEST"]
    if dy > 0:
        return ["SOUTH"]
    if dy < 0:
        return ["NORTH"]
    return None


def tile_at(tiles, pos):
    x, y = pos
    if 0 <= y < len(tiles) and 0 <= x < len(tiles[y]):
        return tiles[y][x]
    return None


def make_replayer(plan, cfg):
    stats = Counter()

    def agent(observation, configuration=None):
        step = int(observation.get("step", 0))
        seat = int(observation.get("player", 0) or 0)
        if step >= len(plan):
            return {"farmer": ["PASS"], "hands": [], "market": []}
        want = plan[step]
        nxt = plan[step + 1] if step + 1 < len(plan) else want
        farm = observation["farms"][seat]
        private = observation["private"]
        cur_pos = [tuple(farm["farmer"])] + [tuple(p) for p in farm["hands"]]
        n_units = len(cur_pos)
        stats["steps"] += 1

        units = []
        for i in range(n_units):
            act = want["units"][i] if i < len(want["units"]) else ["PASS"]
            if not cfg["correct_position"]:
                units.append(act)
                continue
            target_now = want["pos"][i] if i < len(want["pos"]) else None
            target_next = nxt["pos"][i] if i < len(nxt["pos"]) else target_now
            if target_now is None:
                units.append(["PASS"])
                continue
            if cur_pos[i] == target_now:
                if cfg["dig_weeds"] and isinstance(act, (list, tuple)) and act and act[0] in ("PLANT", "BUILD_PASTURE", "BUILD_COOP"):
                    t = tile_at(farm["tiles"], cur_pos[i])
                    if isinstance(t, dict) and t.get("kind") == "WEED":
                        units.append(["DIG"])
                        stats["dug"] += 1
                        continue
                units.append(act)
            else:
                mv = step_toward(cur_pos[i], target_next if target_next else target_now)
                stats["corrected"] += 1
                units.append(mv or ["PASS"])

        market = []
        if cfg["catch_up"]:
            # hands: chase the count the recording will have a few steps from now,
            # so a hire that has to wait for cash is still in place in time
            ahead = plan[min(step + cfg["hire_lookahead"], len(plan) - 1)]["hands"]
            missing = max(want["hands"], ahead) - (n_units - 1)
            for _ in range(max(0, min(missing, cfg["max_catch_up"]))):
                market.append(["HIRE"])
                stats["hire"] += 1
            # land
            if len(farm["unlocked_quadrants"]) < want["quadrants"]:
                market.append(["BUY_LAND"])
                stats["land"] += 1
            # seeds and animals
            for crop, n in want["seeds"].items():
                have = int(private.get("seeds", {}).get(crop, 0))
                if have < n:
                    market.append(["BUY_SEED", crop, min(n - have, cfg["max_catch_up"])])
                    stats["seed"] += 1
            for animal, n in want["animals"].items():
                have = int(private["shed"].get(animal, 0))
                if have < n:
                    market.append(["BUY_ANIMAL", animal, min(n - have, cfg["max_catch_up"])])
                    stats["animal"] += 1
        # the recording's own orders. SELL quantities are the recording's stock,
        # not ours, so post what we actually hold; sells go first because a
        # dropped sell is lost income while a dropped purchase retries next step.
        shed = dict(private["shed"])
        sells, others = [], []
        for o in want["market"]:
            if o[0] == "SELL" and len(o) >= 3 and o[1] in PRODUCTS:
                have = int(shed.get(o[1], 0))
                if have <= 0:
                    continue
                q = have if cfg["sell_stock"] else min(int(o[2]), have)
                shed[o[1]] = have - q
                sells.append(["SELL", o[1], q])
            elif not (cfg["catch_up"] and o[0] in {x[0] for x in market}):
                others.append(list(o))
        market = sells + market + others if cfg["sell_first"] else sells + market + others
        action = {"farmer": units[0], "hands": units[1:], "market": market[:10]}
        return action

    agent.stats = stats
    return agent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--team", required=True)
    parser.add_argument("--opponent", type=Path, default=SHIPPED)
    args = parser.parse_args()
    rep = json.loads(args.replay.read_text())
    names = rep["info"]["TeamNames"]
    seat = names.index(args.team)
    seed = rep["info"].get("seed")
    plan = extract(rep, seat)
    original = rep["steps"][-1][seat]["reward"]
    print(f"{args.replay.name} seat {seat} ({args.team}) seed {seed}: original money {original:,.0f}")
    base = {"correct_position": True, "catch_up": True, "dig_weeds": True, "max_catch_up": 4,
            "hire_lookahead": 0, "sell_stock": False, "sell_first": True}
    ladder = [
        ("raw replay", {**base, "correct_position": False, "catch_up": False, "dig_weeds": False}),
        ("+ catch-up", {**base, "correct_position": False, "dig_weeds": False}),
        ("+ position", {**base, "dig_weeds": False}),
        ("+ weeds", dict(base)),
        ("+ hire lookahead 6", {**base, "hire_lookahead": 6}),
        ("+ sell our stock", {**base, "hire_lookahead": 6, "sell_stock": True}),
    ]
    for label, cfg in ladder:
        a = make_replayer(plan, cfg)
        opp = load_agent(args.opponent, f"corr:{label}:{seed}")
        players = [a, opp] if seat == 0 else [opp, a]
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
        env.run(players)
        money = env.steps[-1][seat]["reward"]
        # how long did the farm stay on plan?
        first = None
        for s in range(1, 720):
            f = env.steps[s][seat]["observation"]["farms"][seat] if "farms" in env.steps[s][seat]["observation"] else env.steps[s][0]["observation"]["farms"][seat]
            if len(f["hands"]) != plan[min(s, 718)]["hands"]:
                first = s
                break
        print(f"  {label:24s} money {money:>10,.0f}  ({money / original:5.1%} of original)  "
              f"first hand-count divergence {first}  stats {dict(a.stats)}")
        for k in [k for k in sys.modules if k.startswith("remap_")]:
            sys.modules.pop(k, None)


if __name__ == "__main__":
    main()
