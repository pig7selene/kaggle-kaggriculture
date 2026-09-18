"""Score a candidate against the agents people are actually running.

Our A/Bs have used a plain public chassis as the opponent, but every band above
2,000 is full of forks of that chassis carrying their own market layers, and
selling harder pays against a passive opponent while costing money against an
active one. This plays a candidate against each extracted public agent over the
same paired seeds and reports per-opponent and pooled records, so a layer that
only wins against a passive chassis cannot hide.
"""
from __future__ import annotations
import argparse, gc, json, statistics, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--variants", required=True, help="comma-separated candidate stems")
    ap.add_argument("--opponents", default="v48,v47,alp,pub_tetsutani_market-smart-farming-kag,pub_tetsutani_shop-aware-farming-kaggr,pub_alperen5252525_kaggriculture-ready")
    ap.add_argument("--pair-every", type=int, default=16)
    ap.add_argument("--seed-slice", default="0:2")
    ap.add_argument("--engine", default="1.32.7")
    ap.add_argument("--tag", default="pool")
    a = ap.parse_args()
    rows = {}
    for v in a.variants.split(","):
        for o in a.opponents.split(","):
            if v == o:
                continue
            name = f"{a.tag}_{v[:18]}_vs_{o[:18]}"
            cmd = [sys.executable, "run_market_layer_ab.py", "--variant", str(VD / f"{v}.py"),
                   "--name", name, "--pair-every", str(a.pair_every), "--seed-slice", a.seed_slice,
                   "--engine", a.engine, "--opponent", str(VD / f"{o}.py")]
            r = subprocess.run(cmd, capture_output=True, text=True)
            line = [l for l in r.stdout.splitlines() if "W/L/T" in l]
            f = ROOT / "experiments" / f"market_layer_ab_{name}.rows.jsonl"
            margins = [json.loads(l)["margin"] for l in f.read_text().splitlines() if '"margin"' in l] if f.is_file() else []
            if margins:
                w = sum(1 for m in margins if m > 0)
                rows.setdefault(v, {})[o] = {"n": len(margins), "w": w, "mean": statistics.mean(margins),
                                             "median": statistics.median(margins), "worst": min(margins)}
                print(f"  {v[:24]:24s} vs {o[:26]:26s} {w}/{len(margins)-w} mean {statistics.mean(margins):+7,.0f} "
                      f"median {statistics.median(margins):+7,.0f} worst {min(margins):+8,.0f}", flush=True)
            else:
                print(f"  {v[:24]:24s} vs {o[:26]:26s} FAILED {(r.stderr or '')[-120:]}", flush=True)
    print("\n=== pooled ===")
    for v, per in rows.items():
        allm = [(d["mean"], d["n"], d["w"]) for d in per.values()]
        n = sum(x[1] for x in allm); w = sum(x[2] for x in allm)
        print(f"  {v[:30]:30s} {w}/{n-w} ({w/max(1,n):.0%}) pooled mean {statistics.mean(x[0] for x in allm):+,.0f} "
              f"| worst opponent {min(per.items(), key=lambda kv: kv[1]['mean'])[0][:24]} {min(d['mean'] for d in per.values()):+,.0f}")
    (ROOT / "experiments" / f"{a.tag}_eval.json").write_text(json.dumps(rows, indent=1) + "\n")


if __name__ == "__main__":
    main()
