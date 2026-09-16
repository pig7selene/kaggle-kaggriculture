"""How much is left in *when* we sell? An upper bound for a sell-timing planner.

Plays one game with every fill logged, then asks: holding the opponent's sales
and the town's consumption fixed, if our premium units could be sold at any
step from the moment they reach the shed, what is the most they could earn?
Relaxations (all in the planner's favour): shed capacity and end-of-day
destruction ignored, our units may be re-ordered freely, the opponent does not
react. The k-th unit we sell faces inventory_without_us(t) + k - 1, since every
unit we sell above the floor stays in the market for good.

If actual revenue is close to this bound, a timing planner has nothing to win.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys

from kaggle_environments import make
import kaggle_environments.envs.kaggriculture.kaggriculture as K

from run_route_remap_pilot import BASE, load_agent

PREM = ("WOOL", "MILK", "STRAWBERRY", "MELON")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", type=Path, default=BASE)
    parser.add_argument("--opponent", type=Path, default=BASE)
    parser.add_argument("--seed", type=int, default=4242)
    args = parser.parse_args()

    log, cur = [], {"step": None, "farms": None}
    orig_pm, orig_cu = K._process_market, K._commit_unit

    def pm(state, env):
        cur["step"] = int(state[0].observation.step)
        cur["farms"] = [id(f) for f in state[0].observation.farms]
        return orig_pm(state, env)

    def cu(op, item, price, farm, private, market, shed_capacity=100):
        ok = orig_cu(op, item, price, farm, private, market, shed_capacity)
        if ok and op == "SELL":
            log.append((cur["step"], cur["farms"].index(id(farm)), item, price))
        return ok

    K._process_market, K._commit_unit = pm, cu
    a = load_agent(args.agent, f"a:{args.seed}")
    b = load_agent(args.opponent, f"b:{args.seed}")
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": args.seed}, debug=False)
    env.run([a, b])
    steps = env.steps
    print(f"{args.agent.parent.name} vs {args.opponent.parent.name} seed {args.seed}: "
          f"money {steps[-1][0]['reward']:,.0f} / {steps[-1][1]['reward']:,.0f}")

    total_actual = total_bound = 0
    print("| item | units | actual revenue | avg | re-timed bound | avg | headroom |")
    for item in PREM:
        ours = [(s, p) for s, q, it, p in log if q == 0 and it == item]
        if not ours:
            continue
        actual = sum(p for _, p in ours)
        # inventory path without our above-floor sales
        cum = 0
        inv_wo = []
        our_nf_by_step = defaultdict(int)
        for s, p in ours:
            if p > 1:
                our_nf_by_step[s] += 1
        for t in range(719):
            inv_wo.append(steps[t][0]["observation"]["market"]["inventory"][item] - cum)
            cum += our_nf_by_step[t]
        # arrivals: shed delta + fills = deposits
        arrivals = []
        for t in range(718):
            shed0 = steps[t][0]["observation"]["private"]["shed"].get(item, 0)
            shed1 = steps[t + 1][0]["observation"]["private"]["shed"].get(item, 0)
            fills = sum(1 for s, _ in ours if s == t)
            dep = shed1 - shed0 + fills
            arrivals.extend([t + 1] * max(0, dep))
        # units in the shed at step 0 count as arrived at 0
        arrivals = [0] * max(0, len(ours) - len(arrivals)) + sorted(arrivals)
        arrivals = arrivals[:len(ours)]
        bound = 0
        for k, arr in enumerate(sorted(arrivals)):
            best_inv = min(inv_wo[t] for t in range(arr, 719))
            bound += K.market_price(item, best_inv + k)
        total_actual += actual
        total_bound += bound
        print(f"| {item} | {len(ours)} | {actual:,.0f} | {actual / len(ours):.0f} | {bound:,.0f} | {bound / len(ours):.0f} | {bound - actual:+,.0f} |")
    print(f"total premium: actual {total_actual:,.0f}, bound {total_bound:,.0f}, headroom {total_bound - total_actual:+,.0f} "
          f"({(total_bound - total_actual) / max(1, steps[-1][0]['reward']) * 100:.1f}% of final money)")


if __name__ == "__main__":
    main()
