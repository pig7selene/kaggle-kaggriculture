"""Can a recorded game be replayed, and does a top agent's tape transfer?

Three questions, in order:
  1. Determinism. Replay both seats' recorded actions as pure tapes on the
     episode's own seed. If the money matches the original, the engine is
     reproducible from the seed plus both action sequences.
  2. Robustness. Replay the target seat's tape against a *different* opponent
     (shipped V43) on the same seed. Money now says what the tape is worth when
     the shared market and the shop draw are no longer the recorded ones.
  3. Where it breaks. Compare the farm's physical state -- tiles, shed, hands,
     money -- between the original and the replay, and report the first step at
     which they part company.
"""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import sys

from kaggle_environments import make

from analyze_v27_routes import normalized_action
from run_route_remap_pilot import load_agent

ROOT = Path(__file__).resolve().parent
SHIPPED = Path("/private/tmp/kaggriculture_v43_variants/shipped.py")


def tape_agent(actions):
    def agent(observation, configuration=None):
        step = observation.get("step", 0) if isinstance(observation, dict) else getattr(observation, "step", 0)
        step = int(step)
        return actions[step] if 0 <= step < len(actions) else {"farmer": ["PASS"], "hands": [], "market": []}
    return agent


def farm_state(obs, seat):
    farms = obs["farms"] if "farms" in obs else None
    f = farms[seat]
    tiles = []
    for row in f["tiles"]:
        for t in row:
            tiles.append(t["kind"] if isinstance(t, dict) else str(t))
    return {"hands": len(f["hands"]), "farmer": tuple(f["farmer"]), "tiles": tuple(tiles),
            "quadrants": tuple(sorted(f["unlocked_quadrants"])), "money": f["money"]}


def physical(state):
    """Everything except money: money moves with the shared market, the farm does not."""
    return {k: v for k, v in state.items() if k != "money"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--team", required=True)
    args = parser.parse_args()
    rep = json.loads(args.replay.read_text())
    names = rep["info"]["TeamNames"]
    seat = names.index(args.team)
    seed = rep["info"].get("seed")
    tapes = [[normalized_action(rep, p, s) for s in range(719)] for p in (0, 1)]
    orig_money = [rep["steps"][-1][p]["reward"] for p in (0, 1)]
    orig_shops = rep["steps"][-1][0]["observation"]["town"]["unlocked_shops"]
    print(f"{args.replay.name}: {names}, seed {seed}, money {orig_money}, shops {orig_shops}")

    print("\n1. both tapes, same seed")
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run([tape_agent(tapes[0]), tape_agent(tapes[1])])
    money = [env.steps[-1][p]["reward"] for p in (0, 1)]
    shops = env.steps[-1][0]["observation"]["town"]["unlocked_shops"]
    print(f"   money {money} (original {orig_money}) | shops {shops}")
    first = None
    for s in range(1, 720):
        a = physical(farm_state(rep["steps"][s][0]["observation"], seat))
        b = physical(farm_state(env.steps[s][0]["observation"], seat))
        if a != b:
            first = s
            diffs = [k for k in a if a[k] != b[k]]
            print(f"   first physical divergence at step {s}: {diffs}")
            for k in diffs:
                if k == "tiles":
                    bad = [(i, a[k][i], b[k][i]) for i in range(len(a[k])) if a[k][i] != b[k][i]][:4]
                    print(f"      tiles: {bad}")
                else:
                    print(f"      {k}: original {a[k]} replay {b[k]}")
            break
    if first is None:
        print("   identical physical state for all 720 steps")

    print("\n2. target tape vs shipped V43, same seed")
    for k in [k for k in sys.modules if k.startswith("remap_")]:
        sys.modules.pop(k, None)
    gc.collect()
    ship = load_agent(SHIPPED, f"tt:{seed}")
    players = [tape_agent(tapes[seat]), ship] if seat == 0 else [ship, tape_agent(tapes[seat])]
    env2 = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env2.run(players)
    m2 = [env2.steps[-1][p]["reward"] for p in (0, 1)]
    print(f"   money {m2} (tape seat {seat}: {m2[seat]:,.0f} vs its original {orig_money[seat]:,.0f}; shipped: {m2[1 - seat]:,.0f})")
    print(f"   shops {env2.steps[-1][0]['observation']['town']['unlocked_shops']}")
    print("   step | original money / replay money | original tiles(PLANT,PASTURE,COOP,WEED) / replay")
    for s in (72, 144, 216, 288, 360, 432, 504, 576, 648, 719):
        oa = farm_state(rep["steps"][s][0]["observation"], seat)
        ob = farm_state(env2.steps[s][0]["observation"], seat)
        cnt = lambda st: tuple(sum(1 for t in st["tiles"] if t == k) for k in ("PLANT", "PASTURE", "COOP", "WEED"))
        print(f"   {s:4d} | {oa['money']:9,.0f} / {ob['money']:9,.0f} | {cnt(oa)} / {cnt(ob)} | hands {oa['hands']}/{ob['hands']}")
    for s in range(1, 720):
        a = physical(farm_state(rep["steps"][s][0]["observation"], seat))
        b = physical(farm_state(env2.steps[s][0]["observation"], seat))
        if a != b:
            diffs = [k for k in a if a[k] != b[k]]
            print(f"   first physical divergence at step {s}: {diffs}")
            for k in diffs:
                if k == "tiles":
                    bad = [(i, a[k][i], b[k][i]) for i in range(len(a[k])) if a[k][i] != b[k][i]][:4]
                    print(f"      tiles: {bad}")
                else:
                    print(f"      {k}: original {a[k]} replay {b[k]}")
            break
    else:
        print("   identical physical state for all 720 steps")


if __name__ == "__main__":
    main()
