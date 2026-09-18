"""Is the fork's post-opening play a per-town program, or a reaction?

If Driz Lo replays a fixed schedule chosen by the town, two of its games in the
same town will agree step for step, the way two games of a taped agent do, and
we can lift that schedule out with the replayer we already have -- which matters
because unlike Majkel's, its farm is the V43 farm, so the plan should transfer.
If instead it is reacting to prices or to the rival, agreement will be no higher
within a town than across towns and only its rules are extractable.

Actions are compared after normalising to the field form -- unit operations
only, not market orders -- from step 144 on, with the tape's own agreement and
the cross-town agreement as the two reference points.
"""
from __future__ import annotations
import argparse, gc, json, statistics
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field

ROOT = Path(__file__).resolve().parent


def sequence(rep, seat, lo=144, hi=719):
    return [field(normalized_action(rep, seat, s)) for s in range(lo, hi)]


def agreement(a, b):
    n = min(len(a), len(b))
    return sum(1 for i in range(n) if a[i] == b[i]) / n if n else 0.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--submissions", default="56327389,56295783")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--shops", type=int, default=2, help="how many opening shops define a town group")
    a = ap.parse_args()
    ours, theirs, towns = [], [], []
    n = 0
    for sid in a.submissions.split(","):
        man = json.loads((ROOT / "experiments" / f"online_{sid.strip()}_episodes_manifest.json").read_text())
        for e in man["episodes"]:
            if n >= a.limit:
                break
            p = Path(e["file"])
            if not p.is_file():
                continue
            rep = json.loads(p.read_text())
            names = rep["info"]["TeamNames"]
            if names[0] == names[1]:
                continue
            seat = e["seat"]
            town = tuple(rep["steps"][600][0]["observation"]["town"]["unlocked_shops"][: a.shops])
            ours.append(sequence(rep, seat))
            theirs.append(sequence(rep, 1 - seat))
            towns.append(town)
            n += 1
            del rep
            if n % 20 == 0:
                print(f"  {n} replays read", flush=True)
                gc.collect()
    print(f"\n{n} games, {len(set(towns))} distinct opening-shop pairs")
    groups = defaultdict(list)
    for i, t in enumerate(towns):
        groups[t].append(i)
    within, cross, opp_within = [], [], []
    for t, idx in groups.items():
        for i, j in combinations(idx, 2):
            within.append(agreement(ours[i], ours[j]))
            opp_within.append(agreement(theirs[i], theirs[j]))
    keys = list(groups)
    for x in range(len(keys)):
        for y in range(x + 1, len(keys)):
            for i in groups[keys[x]][:3]:
                for j in groups[keys[y]][:3]:
                    cross.append(agreement(ours[i], ours[j]))
    def show(name, v):
        if not v:
            print(f"  {name}: no pairs")
            return
        print(f"  {name}: n={len(v):5d} mean {statistics.mean(v):.1%} median {statistics.median(v):.1%} "
              f"max {max(v):.1%} min {min(v):.1%}")
    print("\nstep-for-step agreement between two games (unit actions, steps 144-718):")
    show("the fork, same opening shops ", within)
    show("the fork, different shops    ", cross)
    show("its opponents, same shops    ", opp_within)
    big = sorted(groups.items(), key=lambda kv: -len(kv[1]))[:6]
    print("\nlargest town groups:")
    for t, idx in big:
        v = [agreement(ours[i], ours[j]) for i, j in combinations(idx, 2)]
        if v:
            print(f"  {'+'.join(s[:5] for s in t):24s} n={len(idx):2d} pairs={len(v):3d} mean {statistics.mean(v):.1%} max {max(v):.1%}")


if __name__ == "__main__":
    main()
