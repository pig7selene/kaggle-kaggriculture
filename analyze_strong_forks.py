"""What do the V43 forks in the top-30 band do that the shipped notebook does not?

Five teams in the 2956-3020 band share V43's opening tape: Catalyst, Thomas
Tschinkel, mikelou1, Driz Lo and Kaggriculture Agent. They run our chassis and
rate 400 points above us, so their delta from shipped V43 is the recipe. For
each of their seats this replays the recorded observations through shipped and
reports where the two part company: which route the field actions follow, how
the market orders differ, how premium lots move in time, and what the realized
price index and volume look like.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
import json
from pathlib import Path
import runpy
import statistics
import sys

import pandas as pd

from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field
from run_route_remap_pilot import load_agent

ROOT = Path(__file__).resolve().parent
SHIPPED = Path("/private/tmp/kaggriculture_v43_variants/shipped.py")
PREM = ("WOOL", "MILK", "STRAWBERRY", "MELON")
BASEP = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
         "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
PRODUCTS = tuple(BASEP)


def full_obs(rep, s, seat):
    o = dict(rep["steps"][s][seat]["observation"])
    for k in ("step", "day", "hour", "farms", "market", "town"):
        if k not in o:
            o[k] = rep["steps"][s][0]["observation"][k]
    return o


def shipped_actions(rep, seat, tag):
    agent = load_agent(SHIPPED, tag)
    acts = []
    for s in range(719):
        try:
            acts.append(agent(full_obs(rep, s, seat), rep.get("configuration")))
        except Exception:
            acts.append({"farmer": ["PASS"], "hands": [], "market": []})
    for k in [k for k in sys.modules if k.startswith("remap_")]:
        sys.modules.pop(k, None)
    gc.collect()
    return acts


def market_list(a):
    return [list(o) for o in (a.get("market") or []) if o]


def lots(get, items=PREM):
    out = []
    for s in range(144, 719):
        for o in (get(s).get("market") or []):
            if o and o[0] == "SELL" and len(o) > 2 and o[1] in items and int(o[2]) > 0:
                out.append((s, o[1], int(o[2])))
    return out


def fills(rep, seat, get):
    u = Counter()
    v = Counter()
    for s in range(144, 719):
        shed = dict(full_obs(rep, s, seat)["private"]["shed"])
        prices = rep["steps"][s][0]["observation"]["market"]["prices"]
        for o in (get(s).get("market") or []):
            if o and o[0] == "SELL" and len(o) > 2 and o[1] in PRODUCTS:
                q = min(int(o[2]), int(shed.get(o[1], 0)))
                shed[o[1]] = int(shed.get(o[1], 0)) - q
                u[o[1]] += q
                v[o[1]] += q * prices[o[1]]
    return u, v


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--teams", default="Catalyst,Thomas Tschinkel,mikelou1,Driz Lo,Kaggriculture Agent")
    parser.add_argument("--dir", type=Path, default=Path("/private/tmp/kaggriculture_daily_0916"))
    parser.add_argument("--per-team", type=int, default=3)
    parser.add_argument("--out", type=Path, default=ROOT / "experiments" / "strong_forks_0916.md")
    args = parser.parse_args()
    teams = [t for t in args.teams.split(",") if t]
    man = pd.read_csv(args.dir / "manifest.csv").sort_values("avg_score")
    ns = runpy.run_path(str(SHIPPED), run_name="v43ship")
    routes, route0 = ns["_ROUTES"], ns["_ROUTES"][0]
    rows = []
    seen = Counter()
    for _, m in man.iterrows():
        if all(seen[t] >= args.per_team for t in teams):
            break
        p = args.dir / f"{int(m.episode_id)}.json"
        if not p.is_file():
            continue
        rep = json.loads(p.read_text())
        names = rep["info"]["TeamNames"]
        for seat, team in enumerate(names):
            if team not in teams or seen[team] >= args.per_team:
                continue
            acts = [normalized_action(rep, seat, s) for s in range(719)]
            if sum(field(acts[s]) == field(route0[s]) for s in range(144)) / 144 < 0.9:
                continue
            seen[team] += 1
            base = shipped_actions(rep, seat, f"sf:{m.episode_id}:{seat}")
            best = sorted(((sum(field(acts[s]) == field(routes[r][s]) for s in range(144, 648)) / 504, r)
                           for r in routes if len(routes[r]) >= 648), reverse=True)[:2]
            on, bs = lots(lambda s: acts[s]), lots(lambda s: base[s])
            used, shift, unmatched = set(), Counter(), 0
            for s, it, q in on:
                cands = [(abs(t - s), i) for i, (t, it2, q2) in enumerate(bs)
                         if it2 == it and q2 == q and i not in used and abs(t - s) <= 24]
                if not cands:
                    unmatched += 1
                    continue
                _, i = min(cands)
                used.add(i)
                shift[s - bs[i][0]] += 1
            u, v = fills(rep, seat, lambda s: acts[s])
            ub, vb = fills(rep, seat, lambda s: base[s])
            rows.append({
                "episode_id": int(m.episode_id), "team": team, "score": float(m.min_score),
                "money": rep["rewards"][seat], "opp": names[1 - seat], "opp_money": rep["rewards"][1 - seat],
                "field_agree": round(sum(field(acts[s]) == field(base[s]) for s in range(144, 719)) / 575, 3),
                "market_agree": round(sum(market_list(acts[s]) == market_list(base[s]) for s in range(144, 719)) / 575, 3),
                "best_route": best[0][1], "best_route_agree": round(best[0][0], 3),
                "shipped_route_agree": round(sum(field(acts[s]) == field(base[s]) for s in range(144, 648)) / 504, 3),
                "prem_lots": len(on), "prem_lots_base": len(bs), "unmatched": unmatched,
                "shift": {str(k): n for k, n in sorted(shift.items()) if n},
                "units": {k: u[k] for k in sorted(u, key=lambda k: -v[k])},
                "units_base": {k: ub[k] for k in sorted(ub, key=lambda k: -vb[k])},
                "revenue": sum(v.values()), "revenue_base": sum(vb.values()),
                "prem_index": (sum(v[k] for k in PREM) / max(1, sum(u[k] for k in PREM))
                               / statistics.mean(BASEP[k] for k in PREM)),
            })
            print(f"  {team[:20]:20s} ep {int(m.episode_id)} money {rep['rewards'][seat]:>9,.0f} "
                  f"field {rows[-1]['field_agree']:.2f} market {rows[-1]['market_agree']:.2f} "
                  f"route {rows[-1]['best_route']}@{rows[-1]['best_route_agree']:.2f} "
                  f"lots {len(on)}/{len(bs)} unmatched {unmatched} shift {rows[-1]['shift']} "
                  f"rev {rows[-1]['revenue']:,.0f} vs shipped {rows[-1]['revenue_base']:,.0f}", flush=True)
    args.out.with_suffix(".rows.json").write_text(json.dumps(rows, indent=0) + "\n")
    lines = [f"# V43 forks in the top-30 band, against shipped ({args.dir.name})", "",
             f"{len(rows)} seats.", "",
             "| team | n | score | money | field agr. | market agr. | best route | premium lots (theirs/shipped) | unmatched | revenue (theirs/shipped) |",
             "|---|---:|---:|---:|---:|---:|---|---|---:|---|"]
    by = defaultdict(list)
    for r in rows:
        by[r["team"]].append(r)
    for team, sub in sorted(by.items(), key=lambda kv: -statistics.mean(x["score"] for x in kv[1])):
        mean = lambda k: statistics.mean(x[k] for x in sub)
        lines.append(f"| {team} | {len(sub)} | {mean('score'):.0f} | {mean('money'):,.0f} | {mean('field_agree'):.2f} | "
                     f"{mean('market_agree'):.2f} | {Counter(x['best_route'] for x in sub).most_common(1)[0][0]}"
                     f"@{mean('best_route_agree'):.2f} | {mean('prem_lots'):.0f}/{mean('prem_lots_base'):.0f} | "
                     f"{mean('unmatched'):.0f} | {mean('revenue'):,.0f}/{mean('revenue_base'):,.0f} |")
    agg = Counter()
    for r in rows:
        for k, n in r["shift"].items():
            agg[int(k)] += n
    tot = sum(agg.values()) or 1
    lines += ["", "## Premium lot timing versus shipped (matched lots, all seats)", "",
              ", ".join(f"{k:+d}: {n / tot:.2f}" for k, n in sorted(agg.items()) if n / tot >= 0.005)]
    lines += ["", "## Units sold, theirs vs shipped's counterfactual", "", "| team | theirs | shipped |", "|---|---|---|"]
    for team, sub in by.items():
        u = Counter()
        ub = Counter()
        for r in sub:
            u.update(r["units"])
            ub.update(r["units_base"])
        n = len(sub)
        lines.append(f"| {team} | {', '.join(f'{k} {v / n:.0f}' for k, v in u.most_common())} | "
                     f"{', '.join(f'{k} {v / n:.0f}' for k, v in ub.most_common())} |")
    text = "\n".join(lines) + "\n"
    args.out.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
