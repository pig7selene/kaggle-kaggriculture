"""Who are we playing online, and how do we do against each kind?

For a submission's downloaded episodes (pull_submission_episodes.py): classify
each opponent by its opening -- the fraction of steps 0-143 whose field actions
equal V43 route 0's, which is the same for every V43-lineage fork -- and report
record and margin by class, the losses in detail, and the realized premium
price index for both sides. The premium-lead layers only pay against opponents
that race our lots, so the lineage share of the pool is the number that decides
between lead5-style and adapt5-style agents.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import runpy
import statistics

from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field

ROOT = Path(__file__).resolve().parent
BASE = Path("/private/tmp/kaggriculture_v43_variants/room_plus_clamp.py")
PREM = ("WOOL", "MILK", "STRAWBERRY", "MELON")
BASEP = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}


def price_index(replay, seat):
    units = defaultdict(int); rev = defaultdict(float); floor = defaultdict(int)
    for s in range(719):
        obs = replay["steps"][s][seat]["observation"]
        shed = dict(obs["private"]["shed"]); prices = obs["market"]["prices"]
        for o in normalized_action(replay, seat, s).get("market") or []:
            if not (o and o[0] == "SELL" and len(o) > 2 and o[1] in PREM):
                continue
            q = min(int(o[2]), shed.get(o[1], 0))
            if q <= 0:
                continue
            shed[o[1]] -= q
            units[o[1]] += q; rev[o[1]] += q * prices[o[1]]
            if prices[o[1]] <= 1:
                floor[o[1]] += q
    tot_u = sum(units.values()); tot_base = sum(units[i] * BASEP[i] for i in units)
    return {"units": tot_u, "index": (sum(rev.values()) / tot_base) if tot_base else None,
            "floor_share": (sum(floor.values()) / tot_u) if tot_u else None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=int, required=True)
    parser.add_argument("--lineage-threshold", type=float, default=0.9)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "experiments" / f"online_{args.submission}_episodes_manifest.json").read_text())
    route0 = runpy.run_path(str(BASE), run_name="v43base")["_ROUTES"][0]
    rows = []
    for e in manifest["episodes"]:
        if e.get("opp_team_name") == "pig7selene":
            continue   # the upload's validation episode: a copy of ourselves
        replay = json.loads(Path(e["file"]).read_text())
        seat, opp = e["seat"], 1 - e["seat"]
        agree = sum(field(normalized_action(replay, opp, s)) == field(route0[s]) for s in range(144)) / 144
        shops = replay["steps"][-1][seat]["observation"]["town"]["unlocked_shops"][:2]
        rows.append({**e, "opp_opening_agreement": round(agree, 3),
                     "opp_class": "lineage" if agree >= args.lineage_threshold else "other",
                     "shops": shops, "margin": (e["our_reward"] or 0) - (e["opp_reward"] or 0),
                     "our_price": price_index(replay, seat), "opp_price": price_index(replay, opp)})
    lines = [f"# Online episodes of submission {args.submission}", "",
             f"{len(rows)} episodes downloaded ({manifest['episodes_listed']} listed), record "
             f"{manifest['record']['W']}W/{manifest['record']['L']}L/{manifest['record']['T']}T, pulled {manifest['pulled_at']}.", "",
             "| opponent class | n | W/L/T | mean margin | median margin | our premium index | their premium index | our floor share | their floor share |",
             "|---|---:|---|---:|---:|---:|---:|---:|---:|"]
    for cls in ("lineage", "other"):
        sub = [r for r in rows if r["opp_class"] == cls]
        if not sub:
            continue
        w = sum(r["result"] == "W" for r in sub); l = sum(r["result"] == "L" for r in sub)
        m = [r["margin"] for r in sub]
        idx = lambda k: statistics.mean(r[k]["index"] for r in sub if r[k]["index"] is not None)
        fl = lambda k: statistics.mean(r[k]["floor_share"] for r in sub if r[k]["floor_share"] is not None)
        lines.append(f"| {cls} | {len(sub)} | {w}/{l}/{len(sub) - w - l} | {statistics.mean(m):+,.0f} | {statistics.median(m):+,.0f} | "
                     f"{idx('our_price'):.2f} | {idx('opp_price'):.2f} | {fl('our_price'):.2f} | {fl('opp_price'):.2f} |")
    lines += ["", f"Lineage share of opponents: {sum(r['opp_class'] == 'lineage' for r in rows)}/{len(rows)}.", "",
              "## Losses", "", "| episode | opponent | class | opening agr. | opp rating | shops | our money | their money | margin |", "|---|---|---|---:|---:|---|---:|---:|---:|"]
    for r in sorted((r for r in rows if r["result"] == "L"), key=lambda r: r["margin"]):
        lines.append(f"| {r['episode_id']} | {r['opp_team_name']} | {r['opp_class']} | {r['opp_opening_agreement']:.2f} | {r['opp_score'] or 0:.0f} | "
                     f"{' + '.join(r['shops'])} | {r['our_reward']:,.0f} | {r['opp_reward']:,.0f} | {r['margin']:+,.0f} |")
    lines += ["", "## Rating path (our updatedScore after each episode, chronological)", "",
              " → ".join(f"{r['our_updated_score']:.0f}" for r in sorted(rows, key=lambda r: r["create_time"]) if r["our_updated_score"])]
    text = "\n".join(lines) + "\n"
    out = ROOT / "experiments" / f"online_{args.submission}_lineage.md"
    out.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
