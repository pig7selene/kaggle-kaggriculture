"""How much of the pool sells its premium lots early?

Against plain shipped V43 a five-step lead is worth +1,946 and an eight-step
lead +1,589; against a fork that itself leads eight steps the five-step lead
loses (-162) where the eight-step one wins (+646). Weighting those by the share
x of leading opponents, lead5 beats lead8 whenever x < 31%. So x decides which
agent to submit, and our own online replays measure it: replay each lineage
opponent's observations through shipped, match its premium lots to shipped's by
item and size, and read the timing shift.
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


def lots(get):
    out = []
    for s in range(144, 719):
        for o in (get(s).get("market") or []):
            if o and o[0] == "SELL" and len(o) > 2 and o[1] in PREM and int(o[2]) > 0:
                out.append((s, o[1], int(o[2])))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submissions", default="56296489,56293133")
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--early-threshold", type=int, default=2,
                        help="a lot counts as led if it is sold this many steps or more before shipped's")
    parser.add_argument("--lead-share", type=float, default=0.25,
                        help="fraction of an opponent's matched lots that must be early to call it a leader")
    args = parser.parse_args()
    route0 = runpy.run_path(str(SHIPPED), run_name="v43ship")["_ROUTES"][0]
    rows = []
    for sid in args.submissions.split(","):
        man = json.loads((ROOT / "experiments" / f"online_{sid.strip()}_episodes_manifest.json").read_text())
        for e in man["episodes"]:
            if len(rows) >= args.limit:
                break
            if e.get("opp_team_name") == "pig7selene":
                continue
            rep = json.loads(Path(e["file"]).read_text())
            seat, opp = e["seat"], 1 - e["seat"]
            acts = [normalized_action(rep, opp, s) for s in range(719)]
            if sum(field(acts[s]) == field(route0[s]) for s in range(144)) / 144 < 0.9:
                continue
            base = shipped_actions(rep, opp, f"pl:{e['episode_id']}")
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
            matched = sum(shift.values())
            early = sum(n for d, n in shift.items() if d <= -args.early_threshold)
            rows.append({"episode_id": e["episode_id"], "opp": e.get("opp_team_name"),
                         "score": e.get("opp_score") or 0, "result": e["result"],
                         "margin": (e["our_reward"] or 0) - (e["opp_reward"] or 0),
                         "matched": matched, "unmatched": unmatched,
                         "early": early, "early_share": early / matched if matched else 0.0,
                         "mean_shift": statistics.mean([d for d, n in shift.items() for _ in range(n)]) if matched else 0.0,
                         "submission": sid.strip()})
            print(f"  {e.get('opp_team_name','?')[:20]:20s} matched {matched:3d} early {early:3d} "
                  f"({rows[-1]['early_share']:.0%}) mean shift {rows[-1]['mean_shift']:+.1f} "
                  f"{'LEADER' if rows[-1]['early_share'] >= args.lead_share else ''}", flush=True)
    leaders = [r for r in rows if r["early_share"] >= args.lead_share]
    (ROOT / "experiments" / "pool_lead_share.rows.json").write_text(json.dumps(rows, indent=0) + "\n")
    x = len(leaders) / len(rows) if rows else 0
    print(f"\n{len(rows)} lineage opponents | leaders (>= {args.lead_share:.0%} of lots {args.early_threshold}+ steps early): "
          f"{len(leaders)} -> x = {x:.0%}")
    print(f"mean early share across opponents: {statistics.mean(r['early_share'] for r in rows):.1%}")
    ev5 = 1946 * (1 - x) + (-162) * x
    ev8 = 1589 * (1 - x) + 646 * x
    print(f"expected margin against this pool: lead5 {ev5:+,.0f} | lead8 {ev8:+,.0f} -> "
          f"{'lead5' if ev5 > ev8 else 'lead8'} (break-even at x = 31%)")
    for name, sub in (("we won", [r for r in rows if r["result"] == "W"]), ("we lost", [r for r in rows if r["result"] == "L"])):
        if sub:
            print(f"  {name}: n={len(sub)} mean early share {statistics.mean(r['early_share'] for r in sub):.1%} "
                  f"leaders {sum(1 for r in sub if r['early_share'] >= args.lead_share)}")


if __name__ == "__main__":
    main()
