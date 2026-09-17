"""Do our local games reproduce the online ones?

Every online replay carries its seed (info.seed). Re-simulate each sampled
lineage game locally with the same seed and seats -- our submitted agent bytes
against the local shipped-V43 variant -- under the local 1.32.6 engine and
again with the 1.32.7 market curves patched in, and compare margins with the
online outcome. Agreement means the online opponents really are shipped V43
and the engine is not the gap; disagreement, and the first step at which the
online opponent's action departs from local shipped's, says what they are.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gc
import json
from pathlib import Path
import statistics
import sys

from kaggle_environments import make
import kaggle_environments.envs.kaggriculture.kaggriculture as K

from analyze_v27_routes import normalized_action
from extract_lineage_frontier import field
from run_route_remap_pilot import load_agent

ROOT = Path(__file__).resolve().parent
SHIPPED = Path("/private/tmp/kaggriculture_v43_variants/shipped.py")
ENGINE_1327 = Path("/private/tmp/claude-501/-Users-infiniteejl-Projects-kaggriculture/f8b95bd4-a052-4177-b544-60e3c44ceeac/scratchpad/ke1327/kaggle_environments/envs/kaggriculture/kaggriculture.py")
ORIG = {k: v for k, v in vars(K).items() if k in ("MARKET_PARAMS", "_shape", "market_price")}


def patch_engine(version):
    if version == "1.32.7":
        ns = {}
        exec(compile(ENGINE_1327.read_text(), str(ENGINE_1327), "exec"), ns)
        for k in ("MARKET_PARAMS", "_shape", "market_price", "HINGE_GAIN"):
            if k in ns:
                setattr(K, k, ns[k])
    else:
        for k, v in ORIG.items():
            setattr(K, k, v)


def play(agent_path, opp_path, seed, seat, tag):
    a = load_agent(Path(agent_path), f"rs:a:{tag}")
    b = load_agent(opp_path, f"rs:b:{tag}")
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run([a, b] if seat == 0 else [b, a])
    last = env.steps[-1]
    for k in [k for k in sys.modules if k.startswith("remap_")]:
        sys.modules.pop(k, None)
    gc.collect()
    return env, float(last[seat]["reward"]) - float(last[1 - seat]["reward"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=int, required=True)
    parser.add_argument("--agent", type=Path, required=True, help="our submitted main.py bytes")
    parser.add_argument("--per-class", type=int, default=12, help="games to sample per result (W/L)")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "experiments" / f"online_{args.submission}_episodes_manifest.json").read_text())
    fp = {r["episode_id"]: r for r in json.loads((ROOT / "experiments" / f"online_{args.submission}_fingerprints.rows.json").read_text())} \
        if (ROOT / "experiments" / f"online_{args.submission}_fingerprints.rows.json").exists() else {}
    picks = {"W": [], "L": []}
    for e in manifest["episodes"]:
        if e.get("opp_team_name") == "pig7selene" or e["episode_id"] not in fp:
            continue
        if fp[e["episode_id"]]["best_variant"] != "shipped" or fp[e["episode_id"]]["field_vs_base"] < 0.9:
            continue
        if len(picks[e["result"]]) < args.per_class:
            picks[e["result"]].append(e)
    rows = []
    for res, eps in picks.items():
        for e in eps:
            rep = json.loads(Path(e["file"]).read_text())
            seed = rep["info"].get("seed")
            seat, opp = e["seat"], 1 - e["seat"]
            online = (e["our_reward"] or 0) - (e["opp_reward"] or 0)
            row = {"episode_id": e["episode_id"], "seed": seed, "seat": seat, "online_margin": online, "result": res,
                   "opp": e.get("opp_team_name"), "shops": rep["steps"][-1][0]["observation"]["town"]["unlocked_shops"][:2]}
            for ver in ("1.32.6", "1.32.7"):
                patch_engine(ver)
                env, m = play(args.agent, SHIPPED, seed, seat, f"{e['episode_id']}:{ver}")
                row[f"local_{ver}"] = m
                if ver == "1.32.7":
                    # where does the online opponent first depart from local shipped, and do the shops match?
                    row["local_shops"] = env.steps[-1][0]["observation"]["town"]["unlocked_shops"][:2]
                    div = None
                    for s in range(719):
                        loc = env.steps[s + 1][opp]["action"] if isinstance(env.steps[s + 1][opp].get("action"), dict) else {}
                        onl = normalized_action(rep, opp, s)
                        if field(onl) != field(loc) or [list(o) for o in (onl.get("market") or []) if o] != [list(o) for o in (loc.get("market") or []) if o]:
                            div = s
                            break
                    row["opp_first_divergence"] = div
                    our_div = None
                    for s in range(719):
                        loc = env.steps[s + 1][seat]["action"] if isinstance(env.steps[s + 1][seat].get("action"), dict) else {}
                        onl = normalized_action(rep, seat, s)
                        if field(onl) != field(loc) or [list(o) for o in (onl.get("market") or []) if o] != [list(o) for o in (loc.get("market") or []) if o]:
                            our_div = s
                            break
                    row["our_first_divergence"] = our_div
            patch_engine("1.32.6")
            rows.append(row)
            print(f"  {res} {e['episode_id']} seed {seed} seat {seat} online {online:+,.0f} | local 1.32.6 {row['local_1.32.6']:+,.0f} | 1.32.7 {row['local_1.32.7']:+,.0f} | "
                  f"shops {'same' if row['local_shops'] == row['shops'] else 'DIFF'} | opp diverges at {row['opp_first_divergence']} | we diverge at {row['our_first_divergence']}", flush=True)
    (ROOT / "experiments" / f"online_{args.submission}_resimulation.rows.json").write_text(json.dumps(rows, indent=0) + "\n")
    lines = [f"# Re-simulation of online games: submission {args.submission}", "", f"{len(rows)} games (shipped-fingerprinted, same route).", "",
             "| result online | n | online margin | local 1.32.6 | local 1.32.7 | local W (1.32.7) | shops match | opp median first divergence | ours |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for res in ("W", "L"):
        sub = [r for r in rows if r["result"] == res]
        if sub:
            lines.append(f"| {res} | {len(sub)} | {statistics.mean(r['online_margin'] for r in sub):+,.0f} | {statistics.mean(r['local_1.32.6'] for r in sub):+,.0f} | "
                         f"{statistics.mean(r['local_1.32.7'] for r in sub):+,.0f} | {sum(r['local_1.32.7'] > 0 for r in sub)}/{len(sub)} | {sum(r['local_shops'] == r['shops'] for r in sub)}/{len(sub)} | "
                         f"{statistics.median(r['opp_first_divergence'] if r['opp_first_divergence'] is not None else 719 for r in sub):.0f} | {statistics.median(r['our_first_divergence'] if r['our_first_divergence'] is not None else 719 for r in sub):.0f} |")
    text = "\n".join(lines) + "\n"
    (ROOT / "experiments" / f"online_{args.submission}_resimulation.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
