"""What did each side do that the public V43 base would not have done?

For every downloaded online episode, feed each seat's recorded observations,
in order, to a fresh copy of the room_plus_clamp base and compare the base's
action with the action actually taken. The base is deterministic given the
observation sequence, so the differences are exactly the modifications the
agent carries on top of V43: for our seat, the adaptive lead's interventions;
for a lineage opponent, whatever its author changed. Reported per game and
aggregated by result and by opponent class.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gc
import glob
import json
from pathlib import Path
import statistics
import sys

from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field
from run_route_remap_pilot import BASE, load_agent

ROOT = Path(__file__).resolve().parent
PREM = ("WOOL", "MILK", "STRAWBERRY", "MELON")


def sells(action):
    out = defaultdict(int)
    for o in action.get("market") or []:
        if o and o[0] == "SELL" and len(o) >= 3:
            out[o[1]] += max(0, int(o[2]))
    return out


def counterfactual(rep, seat, tag):
    agent = load_agent(BASE, tag)
    cf = []
    for s in range(719):
        obs = dict(rep["steps"][s][seat]["observation"])
        # replays store shared keys only once: seat 1's observation lacks `step`
        for key in ("step", "day", "hour", "farms", "market", "town"):
            if key not in obs:
                obs[key] = rep["steps"][s][0]["observation"][key]
        try:
            cf.append(agent(obs, rep.get("configuration")))
        except Exception:
            cf.append({"farmer": ["PASS"], "hands": [], "market": []})
    for k in [k for k in sys.modules if k.startswith("remap_")]:
        sys.modules.pop(k, None)
    gc.collect()
    return cf


def diff_stats(rep, seat, cf):
    st = {"market_diff_steps": 0, "field_diff_steps_0_143": 0, "field_diff_steps_144_": 0,
          "prem_extra_units": 0, "prem_missing_units": 0, "prem_extra_steps": 0,
          "other_extra_units": 0, "other_missing_units": 0, "extra_orders": 0}
    for s in range(719):
        act = normalized_action(rep, seat, s)
        base = cf[s]
        if field(act) != field(base):
            st["field_diff_steps_0_143" if s < 144 else "field_diff_steps_144_"] += 1
        a, b = sells(act), sells(base)
        if (act.get("market") or []) != (base.get("market") or []):
            st["market_diff_steps"] += 1
        for item in set(a) | set(b):
            d = a[item] - b[item]
            key = "prem" if item in PREM else "other"
            if d > 0:
                st[f"{key}_extra_units"] += d
                if key == "prem":
                    st["prem_extra_steps"] += 1
            elif d < 0:
                st[f"{key}_missing_units"] += -d
        st["extra_orders"] += max(0, len(act.get("market") or []) - len(base.get("market") or []))
    return st


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=int, required=True)
    parser.add_argument("--limit", type=int, default=400)
    parser.add_argument("--opponents", action="store_true", help="also run the counterfactual for the opponent seat")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "experiments" / f"online_{args.submission}_episodes_manifest.json").read_text())
    import runpy
    route0 = runpy.run_path(str(BASE), run_name="v43base")["_ROUTES"][0]
    rows = []
    for i, e in enumerate(manifest["episodes"][: args.limit]):
        if e.get("opp_team_name") == "pig7selene":
            continue
        rep = json.loads(Path(e["file"]).read_text())
        seat, opp = e["seat"], 1 - e["seat"]
        row = dict(episode_id=e["episode_id"], result=e["result"], margin=(e["our_reward"] or 0) - (e["opp_reward"] or 0),
                   opp=e.get("opp_team_name"), opp_score=e.get("opp_score"),
                   opp_agree=sum(field(normalized_action(rep, opp, s)) == field(route0[s]) for s in range(144)) / 144)
        row["ours"] = diff_stats(rep, seat, counterfactual(rep, seat, f"cf:{e['episode_id']}:{seat}"))
        if args.opponents:
            row["theirs"] = diff_stats(rep, opp, counterfactual(rep, opp, f"cf:{e['episode_id']}:{opp}"))
        rows.append(row)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{len(manifest['episodes'])}", flush=True)
    out = ROOT / "experiments" / f"online_{args.submission}_counterfactual.rows.json"
    out.write_text(json.dumps(rows, indent=0) + "\n")

    def agg(sub, side, key):
        vals = [r[side][key] for r in sub if side in r]
        return statistics.mean(vals) if vals else float("nan")

    lines = [f"# Counterfactual against the V43 base: submission {args.submission}", "", f"{len(rows)} episodes.", ""]
    lines += ["## Our interventions (adaptive lead) by result", "",
              "| result | n | mean margin | prem extra units | prem extra steps | prem missing units | market diff steps | field diff 144+ |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for res in ("W", "L"):
        sub = [r for r in rows if r["result"] == res]
        if sub:
            lines.append(f"| {res} | {len(sub)} | {statistics.mean(r['margin'] for r in sub):+,.0f} | {agg(sub,'ours','prem_extra_units'):.0f} | "
                         f"{agg(sub,'ours','prem_extra_steps'):.0f} | {agg(sub,'ours','prem_missing_units'):.0f} | {agg(sub,'ours','market_diff_steps'):.0f} | {agg(sub,'ours','field_diff_steps_144_'):.0f} |")
    # games where we did not lead vs games where we did
    lin_rows = [r for r in rows if r["opp_agree"] >= 0.9]
    lines += ["", "### Against lineage opponents only: our lead volume vs result", ""]
    if lin_rows:
        qs = statistics.quantiles([r["ours"]["prem_extra_units"] for r in lin_rows], n=3) if len(lin_rows) > 3 else [0, 0]
        for name, sub in (("low lead tercile", [r for r in lin_rows if r["ours"]["prem_extra_units"] <= qs[0]]),
                          ("mid", [r for r in lin_rows if qs[0] < r["ours"]["prem_extra_units"] <= qs[1]]),
                          ("high lead tercile", [r for r in lin_rows if r["ours"]["prem_extra_units"] > qs[1]])):
            if sub:
                c = Counter(r["result"] for r in sub)
                lines.append(f"- {name}: n={len(sub)} W/L {c['W']}/{c['L']} mean margin {statistics.mean(r['margin'] for r in sub):+,.0f} "
                             f"(led units {statistics.mean(r['ours']['prem_extra_units'] for r in sub):.0f})")
    if args.opponents:
        lines += ["", "## Opponents' modifications relative to the base", "",
                  "| opponent class | n | field diff 0-143 | field diff 144+ | market diff steps | prem extra units | prem missing units | other extra | other missing | extra orders |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for cls, sub in (("lineage", [r for r in rows if r["opp_agree"] >= 0.9]), ("other", [r for r in rows if r["opp_agree"] < 0.9])):
            if sub:
                lines.append(f"| {cls} | {len(sub)} | {agg(sub,'theirs','field_diff_steps_0_143'):.0f} | {agg(sub,'theirs','field_diff_steps_144_'):.0f} | "
                             f"{agg(sub,'theirs','market_diff_steps'):.0f} | {agg(sub,'theirs','prem_extra_units'):.0f} | {agg(sub,'theirs','prem_missing_units'):.0f} | "
                             f"{agg(sub,'theirs','other_extra_units'):.0f} | {agg(sub,'theirs','other_missing_units'):.0f} | {agg(sub,'theirs','extra_orders'):.0f} |")
        lin = [r for r in rows if r["opp_agree"] >= 0.9 and "theirs" in r]
        lines += ["", "### Lineage opponents: how many are unmodified V43 (market diff < 20 steps and field diff 144+ < 20)?", ""]
        plain = [r for r in lin if r["theirs"]["market_diff_steps"] < 20 and r["theirs"]["field_diff_steps_144_"] < 20]
        lines.append(f"plain: {len(plain)}/{len(lin)}; our record vs plain {Counter(r['result'] for r in plain)}; vs modified {Counter(r['result'] for r in lin if r not in plain)}")
        lines += ["", "### Lineage opponents that beat us: their modification profile", "",
                  "| opponent | rating | margin | their field diff 144+ | their market diff | their prem extra | their prem missing | our prem extra |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for r in sorted((r for r in lin if r["result"] == "L"), key=lambda r: r["margin"]):
            t = r["theirs"]
            lines.append(f"| {r['opp']} | {r['opp_score'] or 0:.0f} | {r['margin']:+,.0f} | {t['field_diff_steps_144_']} | {t['market_diff_steps']} | {t['prem_extra_units']} | {t['prem_missing_units']} | {r['ours']['prem_extra_units']} |")
    text = "\n".join(lines) + "\n"
    (ROOT / "experiments" / f"online_{args.submission}_counterfactual.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
