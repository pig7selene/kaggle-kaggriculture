"""What do today's top agents do that shipped V43 does not?

The daily episode dataset holds the highest-average-score episodes of a day --
the leaders' games. For each team seat in a sample of them, replay the recorded
observations through shipped V43 and report: opening agreement with V43 route 0
(is this our lineage?), field and market agreement after 144, the lot-level
timing shift of premium sales, production counts, and the realized premium
price index. The counterfactual is exact for a lineage agent, so the deltas are
the modifications that separate a 3100-proxy agent from the public notebook.
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

from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field
from run_route_remap_pilot import load_agent

ROOT = Path(__file__).resolve().parent
SHIPPED = Path("/private/tmp/kaggriculture_v43_variants/shipped.py")
PREM = ("WOOL", "MILK", "STRAWBERRY", "MELON")
BASEP = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
         "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}


def full_obs(rep, s, seat):
    obs = dict(rep["steps"][s][seat]["observation"])
    for key in ("step", "day", "hour", "farms", "market", "town"):
        if key not in obs:
            obs[key] = rep["steps"][s][0]["observation"][key]
    return obs


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


def fills_and_value(rep, seat, get):
    units = rev = 0
    for s in range(144, 719):
        shed = dict(full_obs(rep, s, seat)["private"]["shed"])
        prices = rep["steps"][s][0]["observation"]["market"]["prices"]
        for o in (get(s).get("market") or []):
            if o and o[0] == "SELL" and len(o) > 2 and o[1] in PREM:
                q = min(int(o[2]), int(shed.get(o[1], 0)))
                shed[o[1]] = int(shed.get(o[1], 0)) - q
                units += q
                rev += q * prices[o[1]] / BASEP[o[1]]
    return units, (rev / units if units else None)


def verbs(rep, seat, get):
    c = Counter()
    for s in range(144, 719):
        a = get(s)
        for u in [a.get("farmer")] + list(a.get("hands") or []):
            c[str(u[0]) if isinstance(u, (list, tuple)) and u else "PASS"] += 1
    return c


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    import pandas as pd
    man = pd.read_csv(args.dir / "manifest.csv").sort_values("avg_score", ascending=False)
    route0 = runpy.run_path(str(SHIPPED), run_name="v43ship")["_ROUTES"][0]
    rows = []
    for _, m in man.head(args.episodes).iterrows():
        path = args.dir / f"{int(m.episode_id)}.json"
        if not path.is_file():
            continue
        rep = json.loads(path.read_text())
        names = rep["info"]["TeamNames"]
        for seat in (0, 1):
            acts = [normalized_action(rep, seat, s) for s in range(719)]
            open_agree = sum(field(acts[s]) == field(route0[s]) for s in range(144)) / 144
            row = {"episode_id": int(m.episode_id), "team": names[seat], "seat": seat,
                   "avg_score": float(m.avg_score), "money": rep["steps"][-1][seat]["reward"],
                   "opp_money": rep["steps"][-1][1 - seat]["reward"], "opening_agreement": round(open_agree, 3)}
            if open_agree >= 0.9:
                base = shipped_actions(rep, seat, f"top:{m.episode_id}:{seat}")
                row["field_agree_144"] = round(sum(field(acts[s]) == field(base[s]) for s in range(144, 719)) / 575, 3)
                row["market_agree_144"] = round(sum(market_list(acts[s]) == market_list(base[s]) for s in range(144, 719)) / 575, 3)
                on, bs = lots(lambda s: acts[s]), lots(lambda s: base[s])
                used, shift, unmatched = set(), Counter(), 0
                for s, it, q in on:
                    cands = [(abs(t - s), i) for i, (t, it2, q2) in enumerate(bs) if it2 == it and q2 == q and i not in used and abs(t - s) <= 16]
                    if not cands:
                        unmatched += 1
                        continue
                    _, i = min(cands)
                    used.add(i)
                    shift[s - bs[i][0]] += 1
                row["prem_lots"], row["prem_lots_unmatched"] = len(on), unmatched
                row["prem_lots_base"] = len(bs)
                row["shift"] = {str(k): v for k, v in sorted(shift.items())}
                row["units"], row["price_index"] = fills_and_value(rep, seat, lambda s: acts[s])
                bu, bp = fills_and_value(rep, seat, lambda s: base[s])
                row["units_base"], row["price_index_base"] = bu, bp
                v, vb = verbs(rep, seat, lambda s: acts[s]), verbs(rep, seat, lambda s: base[s])
                row["pass"], row["pass_base"] = v["PASS"], vb["PASS"]
                row["harvest"], row["harvest_base"] = v["HARVEST"], vb["HARVEST"]
            rows.append(row)
            print(f"  {names[seat][:22]:22s} open {open_agree:.2f} " +
                  (f"field {row['field_agree_144']:.2f} market {row['market_agree_144']:.2f} lots {row['prem_lots']}/{row['prem_lots_base']} "
                   f"unmatched {row['prem_lots_unmatched']} shift {row['shift']} units {row['units']}/{row['units_base']} "
                   f"idx {row['price_index'] and round(row['price_index'], 2)}/{row['price_index_base'] and round(row['price_index_base'], 2)} "
                   f"pass {row['pass']}/{row['pass_base']}" if "field_agree_144" in row else "(not lineage)"), flush=True)
    args.out.with_suffix(".rows.json").write_text(json.dumps(rows, indent=0) + "\n")
    lin = [r for r in rows if "field_agree_144" in r]
    lines = [f"# Top agents vs shipped V43 ({args.dir.name})", "",
             f"{len(rows)} seats in {args.episodes} top episodes; {len(lin)} are V43 lineage (opening agreement >= 0.9).", "",
             "| team | n | field agr. | market agr. | premium lots (theirs/shipped) | unmatched | units (theirs/shipped) | price index (theirs/shipped) | PASS (theirs/shipped) | money |",
             "|---|---:|---:|---:|---|---:|---|---|---|---:|"]
    by = defaultdict(list)
    for r in lin:
        by[r["team"]].append(r)
    for team, sub in sorted(by.items(), key=lambda kv: -statistics.mean(x["money"] for x in kv[1])):
        mean = lambda k: statistics.mean(x[k] for x in sub if x.get(k) is not None)
        lines.append(f"| {team} | {len(sub)} | {mean('field_agree_144'):.2f} | {mean('market_agree_144'):.2f} | "
                     f"{mean('prem_lots'):.0f}/{mean('prem_lots_base'):.0f} | {mean('prem_lots_unmatched'):.0f} | "
                     f"{mean('units'):.0f}/{mean('units_base'):.0f} | {mean('price_index'):.2f}/{mean('price_index_base'):.2f} | "
                     f"{mean('pass'):.0f}/{mean('pass_base'):.0f} | {mean('money'):,.0f} |")
    agg = Counter()
    for r in lin:
        for k, v in (r.get("shift") or {}).items():
            agg[int(k)] += v
    tot = sum(agg.values()) or 1
    lines += ["", "## Premium lot timing shift vs shipped (all lineage seats, matched lots)", "",
              ", ".join(f"{k:+d}: {v / tot:.2f}" for k, v in sorted(agg.items()) if v / tot >= 0.005)]
    nonlin = [r for r in rows if "field_agree_144" not in r]
    if nonlin:
        lines += ["", "## Not V43 lineage", "", "| team | opening agreement | money |", "|---|---:|---:|"]
        for r in sorted(nonlin, key=lambda r: -r["money"])[:20]:
            lines.append(f"| {r['team']} | {r['opening_agreement']:.2f} | {r['money']:,.0f} |")
    text = "\n".join(lines) + "\n"
    args.out.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
