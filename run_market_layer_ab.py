"""Direct-match A/B of a V43 variant against the room_plus_clamp base.

The market layers are zero-sum against the opponent, so self-play of the
variant against itself would show nothing; this plays variant vs base on the
same seed in both seats and records the money margin (variant - base).
Pairs are every k-th first-two-shop pair of the seed manifest so a pilot
covers the pair space thinly; seeds are a slice per pair so a holdout can use
seeds the pilot never touched.
"""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import statistics
import sys
import time

from kaggle_environments import make

from run_route_remap_pilot import BASE, load_agent

ROOT = Path(__file__).resolve().parent
SEEDS = ROOT / "experiments" / "seed_first_shops_manifest.json"


def play(variant: Path, seed: int, seat: int, opponent: Path = BASE) -> dict:
    tag = f"{time.time_ns()}"
    v = load_agent(variant, f"v:{tag}")
    b = load_agent(opponent, f"b:{tag}")
    players = [v, b] if seat == 0 else [b, v]
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
    env.run(players)
    last = env.steps[-1]
    row = {"seed": seed, "seat": seat, "steps": len(env.steps),
           "variant_money": last[seat]["reward"], "base_money": last[1 - seat]["reward"],
           "shops": list(last[0]["observation"]["town"]["unlocked_shops"][:2]),
           "telemetry": next((t for k, t in (getattr(v, "telemetry", {}) or {}).items()
                              if k in ("market_layer", "price_gate", "premium_lead", "adaptive_lead")), None)}
    if len(env.steps) != 720 or row["variant_money"] is None or row["base_money"] is None:
        row["error"] = "incomplete"
    else:
        row["margin"] = float(row["variant_money"]) - float(row["base_money"])
    for k in [k for k in sys.modules if k.startswith("remap_")]:
        sys.modules.pop(k, None)
    gc.collect()
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--pair-every", type=int, default=4)
    parser.add_argument("--pair-offset", type=int, default=0)
    parser.add_argument("--seed-slice", default="0:2")
    parser.add_argument("--opponent", type=Path, default=BASE,
                        help="opponent agent main.py (default: room_plus_clamp base)")
    parser.add_argument("--pairs-file", type=Path,
                        help='JSON with {"pairs": [[shopA, shopB], ...]}; overrides --pair-every')
    args = parser.parse_args()
    lo, hi = (int(x) for x in args.seed_slice.split(":"))
    by_pair = json.loads(SEEDS.read_text())["by_pair"]
    if args.pairs_file:
        pairs = [" + ".join(p) for p in json.loads(args.pairs_file.read_text())["pairs"]]
        pairs = [p for p in pairs if p in by_pair]
    else:
        pairs = sorted(by_pair)[args.pair_offset::args.pair_every]
    jobs = [(pair, seed, seat) for pair in pairs for seed in by_pair[pair][lo:hi] for seat in (0, 1)]
    out = ROOT / "experiments" / f"market_layer_ab_{args.name}.rows.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text().splitlines():
            r = json.loads(line)
            done.add((r["pair"], r["seed"], r["seat"]))
    print(f"{args.name}: {len(pairs)} pairs, {len(jobs)} games, {len(done)} already done", flush=True)
    with out.open("a") as fh:
        for i, (pair, seed, seat) in enumerate(jobs):
            if (pair, seed, seat) in done:
                continue
            row = play(args.variant, seed, seat, args.opponent)
            row["pair"] = pair
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            print(f"  {i + 1}/{len(jobs)} {pair} seed {seed} seat {seat} margin {row.get('margin')}", flush=True)
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    ok = [r for r in rows if "margin" in r]
    m = [r["margin"] for r in ok]
    w = sum(1 for x in m if x > 0); l = sum(1 for x in m if x < 0)
    print(f"{args.name} vs {args.opponent.parent.name}: {len(ok)} games W/L/T {w}/{l}/{len(m) - w - l} "
          f"mean {statistics.mean(m):+,.0f} median {statistics.median(m):+,.0f} "
          f"worst {min(m):+,.0f} best {max(m):+,.0f} | errors {len(rows) - len(ok)}")
    per_pair = {}
    for r in ok:
        per_pair.setdefault(r["pair"], []).append(r["margin"])
    for pair, ms in sorted(per_pair.items(), key=lambda kv: statistics.mean(kv[1])):
        print(f"  {statistics.mean(ms):+9,.0f}  {pair}  (n={len(ms)})")
    tel = [r["telemetry"] for r in ok if r.get("telemetry")]
    if tel:
        print("telemetry mean:", {k: round(statistics.mean(t[k] for t in tel), 1) for k in tel[0]})


if __name__ == "__main__":
    main()
