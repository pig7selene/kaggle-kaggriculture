"""Which V43 configuration is each online lineage opponent running?

For every lineage opponent (opening identical to V43 route 0), feed its
recorded observations to each of our V43 switch variants and to the raw route
bank, and ask which one reproduces its actions: market-list equality per step
from 144 on for the layer configuration, field equality for the route. This
turns the anonymous population into a histogram of known configurations, and
our record against each configuration says which ones beat us.
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
VDIR = Path("/private/tmp/kaggriculture_v43_variants")
VARIANTS = ["shipped", "room_plus_clamp", "plus_room_guard", "plus_clamp_sells", "plus_dead_stock",
            "plus_terminal_liquidation", "plus_front_run", "plus_budget_guard", "all_on", "all_on_no_budget", "layers_off"]


def ensure_layers_off():
    out = VDIR / "layers_off.py"
    if not out.exists():
        src = (VDIR / "room_plus_clamp.py").read_text()
        line = next(l for l in src.splitlines() if l.startswith("_SETTINGS="))
        off = ("_SETTINGS={'hand_align': True, 'weed_repair': False, 'sell_lead': False, 'budget_guard': False, "
               "'room_guard': False, 'clamp_sells': False, 'dead_stock': False, 'terminal_liquidation': False, 'front_run': False}")
        out.write_text(src.replace(line, off, 1))


def full_obs(rep, s, seat):
    obs = dict(rep["steps"][s][seat]["observation"])
    for key in ("step", "day", "hour", "farms", "market", "town"):
        if key not in obs:
            obs[key] = rep["steps"][s][0]["observation"][key]
    return obs


def run_variant(rep, seat, variant, tag):
    agent = load_agent(VDIR / f"{variant}.py", tag)
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


def norm_market(a):
    return [list(o) for o in (a.get("market") or []) if o]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=int, required=True)
    parser.add_argument("--limit", type=int, default=400)
    parser.add_argument("--variants", default=",".join(VARIANTS), help="comma-separated variant file stems in the variants dir")
    parser.add_argument("--tag", default="", help="suffix for the output files")
    parser.add_argument("--skip", type=int, default=0, help="skip the first N listed episodes (chronological)")
    args = parser.parse_args()
    ensure_layers_off()
    variants = [v for v in args.variants.split(",") if v]
    manifest = json.loads((ROOT / "experiments" / f"online_{args.submission}_episodes_manifest.json").read_text())
    ns = runpy.run_path(str(VDIR / "room_plus_clamp.py"), run_name="v43base")
    routes, route0 = ns["_ROUTES"], ns["_ROUTES"][0]
    rows = []
    for i, e in enumerate(manifest["episodes"][args.skip: args.skip + args.limit]):
        if e.get("opp_team_name") == "pig7selene":
            continue
        rep = json.loads(Path(e["file"]).read_text())
        seat, opp = e["seat"], 1 - e["seat"]
        actual = [normalized_action(rep, opp, s) for s in range(719)]
        agree0 = sum(field(actual[s]) == field(route0[s]) for s in range(144)) / 144
        if agree0 < 0.9:
            continue
        row = {"episode_id": e["episode_id"], "opp": e.get("opp_team_name"), "opp_score": e.get("opp_score"),
               "result": e["result"], "margin": (e["our_reward"] or 0) - (e["opp_reward"] or 0), "variants": {}}
        for v in variants:
            acts = run_variant(rep, opp, v, f"fp:{e['episode_id']}:{v}")
            mk = sum(norm_market(actual[s]) == norm_market(acts[s]) for s in range(144, 719)) / (719 - 144)
            fd = sum(field(actual[s]) == field(acts[s]) for s in range(144, 719)) / (719 - 144)
            row["variants"][v] = {"market": round(mk, 3), "field": round(fd, 3)}
        best = max(row["variants"], key=lambda v: row["variants"][v]["market"])
        row["best_variant"], row["best_market"] = best, row["variants"][best]["market"]
        row["field_vs_base"] = row["variants"].get("room_plus_clamp", row["variants"][variants[0]])["field"]
        if row["field_vs_base"] < 0.9:
            scores = sorted(((sum(field(actual[s]) == field(routes[r][s]) for s in range(144, 648)) / 504, r)
                             for r in routes if len(routes[r]) >= 648), reverse=True)
            row["best_route"], row["best_route_agree"] = scores[0][1], round(scores[0][0], 3)
        rows.append(row)
        print(f"  {len(rows)} {row['opp'][:20]:20s} best {best:26s} market {row['best_market']:.2f} field-vs-base {row['field_vs_base']:.2f} "
              f"{('route ' + str(row.get('best_route')) + ' @' + str(row.get('best_route_agree'))) if 'best_route' in row else ''}", flush=True)
    (ROOT / "experiments" / f"online_{args.submission}_fingerprints{args.tag}.rows.json").write_text(json.dumps(rows, indent=0) + "\n")

    lines = [f"# Fingerprints of lineage opponents: submission {args.submission}", "", f"{len(rows)} lineage opponents.", "",
             "## Best-matching layer configuration (market list equality, steps 144-718)", "",
             "| configuration | n | mean match | our W/L | mean margin |", "|---|---:|---:|---|---:|"]
    by = defaultdict(list)
    for r in rows:
        by[r["best_variant"]].append(r)
    for v, sub in sorted(by.items(), key=lambda kv: -len(kv[1])):
        c = Counter(r["result"] for r in sub)
        lines.append(f"| {v} | {len(sub)} | {statistics.mean(r['best_market'] for r in sub):.2f} | {c['W']}/{c['L']} | {statistics.mean(r['margin'] for r in sub):+,.0f} |")
    same = [r for r in rows if r["field_vs_base"] >= 0.9]
    diff = [r for r in rows if r["field_vs_base"] < 0.9]
    lines += ["", "## Farm: same route as the base would pick, or a different one?", "",
              f"- same route (field match >= 0.9): {len(same)}, our W/L {Counter(r['result'] for r in same)}, mean margin {statistics.mean(r['margin'] for r in same) if same else 0:+,.0f}",
              f"- different: {len(diff)}, our W/L {Counter(r['result'] for r in diff)}, mean margin {statistics.mean(r['margin'] for r in diff) if diff else 0:+,.0f}"]
    if diff:
        lines += ["", "| best raw route | n | mean agreement | our W/L |", "|---|---:|---:|---|"]
        byr = defaultdict(list)
        for r in diff:
            byr[r.get("best_route")].append(r)
        for rt, sub in sorted(byr.items(), key=lambda kv: -len(kv[1])):
            c = Counter(r["result"] for r in sub)
            lines.append(f"| {rt} | {len(sub)} | {statistics.mean(r['best_route_agree'] for r in sub):.2f} | {c['W']}/{c['L']} |")
    lines += ["", "## Market match distribution (how well does the best configuration explain them?)", "",
              "- " + ", ".join(f"{q:.2f}" for q in statistics.quantiles([r["best_market"] for r in rows], n=4)) + " (quartiles)"]
    text = "\n".join(lines) + "\n"
    (ROOT / "experiments" / f"online_{args.submission}_fingerprints{args.tag}.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
