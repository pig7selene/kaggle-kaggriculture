"""Two agents that look alike, 390 rating points apart: where does it come from?

mikelou1 ranks 56 at 2891 with field actions agreeing with shipped V43 on 0.98
of steps after 144 and total sell revenue within 693 of shipped's counterfactual
on the same observations, while our own shipped-family submissions settle at
2503-2640. Either the difference lives in the fifth of market steps where they
do differ -- in which case it is a state-conditioned rule we can learn -- or our
rating is depressed for a reason that has nothing to do with the agent.

This looks at their games from the side the rating actually counts: who won,
by how much, when the money curves separated, and what the opponent got. It
also reads the same quantities off our own online episodes so the two can be
compared on equal terms.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

import pandas as pd

from analyze_v27_routes import normalized_action

ROOT = Path(__file__).resolve().parent
PRODUCTS = ("CARROT", "EGG", "FERTILIZER", "MELON", "MILK", "STRAWBERRY", "TOMATO", "WHEAT", "WOOL")
CHECKPOINTS = (144, 288, 432, 576, 648, 719)


def obs_of(rep, s, seat):
    o = dict(rep["steps"][s][seat]["observation"])
    for k in ("step", "day", "hour", "farms", "market", "town"):
        if k not in o:
            o[k] = rep["steps"][s][0]["observation"][k]
    return o


def money_curve(rep, seat):
    return [obs_of(rep, s, seat)["farms"][seat]["money"] for s in CHECKPOINTS[:-1]] + [rep["rewards"][seat]]


def profile(rep, seat):
    ours, theirs = money_curve(rep, seat), money_curve(rep, 1 - seat)
    return {"money": rep["rewards"][seat], "opp_money": rep["rewards"][1 - seat],
            "margin": rep["rewards"][seat] - rep["rewards"][1 - seat],
            "curve": ours, "opp_curve": theirs,
            "gap": [a - b for a, b in zip(ours, theirs)]}


def summarize(label, rows):
    if not rows:
        return
    w = sum(1 for r in rows if r["margin"] > 0)
    print(f"\n{label}: n={len(rows)} W/L {w}/{len(rows) - w} "
          f"mean margin {statistics.mean(r['margin'] for r in rows):+,.0f} "
          f"median {statistics.median(r['margin'] for r in rows):+,.0f}")
    print("  money gap at steps " + "/".join(str(c) for c in CHECKPOINTS) + ": " +
          " ".join(f"{statistics.mean(r['gap'][i] for r in rows):+7,.0f}" for i in range(len(CHECKPOINTS))))
    print("  our money  " + " ".join(f"{statistics.mean(r['curve'][i] for r in rows):8,.0f}" for i in range(len(CHECKPOINTS))))
    print("  their money" + " ".join(f"{statistics.mean(r['opp_curve'][i] for r in rows):8,.0f}" for i in range(len(CHECKPOINTS))))
    wins = [r for r in rows if r["margin"] > 0]
    losses = [r for r in rows if r["margin"] <= 0]
    for name, sub in (("wins", wins), ("losses", losses)):
        if sub:
            print(f"  {name}: median margin {statistics.median(r['margin'] for r in sub):+,.0f}, "
                  f"median money {statistics.median(r['money'] for r in sub):,.0f} vs opponent {statistics.median(r['opp_money'] for r in sub):,.0f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--teams", default="mikelou1,Thomas Tschinkel,Driz Lo,Catalyst")
    parser.add_argument("--dirs", default="/private/tmp/kaggriculture_daily_0916,/private/tmp/kaggriculture_daily_0915")
    parser.add_argument("--ours", type=Path, default=ROOT / "experiments" / "online_56274059_episodes_manifest.json")
    args = parser.parse_args()
    teams = [t for t in args.teams.split(",") if t]
    by_team = defaultdict(list)
    opponents = defaultdict(Counter)
    for d in args.dirs.split(","):
        d = Path(d)
        man = pd.read_csv(d / "manifest.csv")
        for _, m in man.iterrows():
            p = d / f"{int(m.episode_id)}.json"
            if not p.is_file():
                continue
            rep = json.loads(p.read_text())
            names = rep["info"]["TeamNames"]
            for seat, t in enumerate(names):
                if t in teams:
                    r = profile(rep, seat)
                    r["episode_id"] = int(m.episode_id)
                    r["opp"] = names[1 - seat]
                    r["create_time"] = m.create_time
                    by_team[t].append(r)
                    opponents[t][names[1 - seat]] += 1
    for t in teams:
        summarize(f"{t} (daily sets)", by_team[t])
        print("  opponents: " + ", ".join(f"{o} {n}" for o, n in opponents[t].most_common(6)))
    if args.ours.is_file():
        man = json.loads(args.ours.read_text())
        rows = []
        for e in man["episodes"]:
            if e.get("opp_team_name") == "pig7selene":
                continue
            rep = json.loads(Path(e["file"]).read_text())
            r = profile(rep, e["seat"])
            r["episode_id"] = e["episode_id"]
            r["opp"] = e.get("opp_team_name")
            rows.append(r)
        summarize("us (adapt5 online)", rows)


if __name__ == "__main__":
    main()
