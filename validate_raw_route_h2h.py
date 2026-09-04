"""Fresh paired confirmation of the strongest route-family challenger."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import statistics
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from kaggle_environments import make

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "experiments" / "autonomous_raw_route_h2h.json"


def load(path):
    name = "raw_h2h_" + hashlib.sha256(str(path).encode()).hexdigest()[:12]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.agent


def run(job):
    candidate, best, seed, seat = job
    c = load(candidate)
    b = load(best)
    pair = [b, b]
    pair[seat] = c
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=True)
    error = None
    try:
        env.run(pair)
    except Exception as exc:
        error = repr(exc)
    if error:
        return {"seed": seed, "seat": seat, "error": error}
    f = env.steps[-1]
    return {"seed": seed, "seat": seat, "candidate_money": float(f[seat].reward), "best_money": float(f[1 - seat].reward), "advantage": float(f[seat].reward - f[1-seat].reward), "error": None}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(17000, 17016)))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    candidate = ROOT / "agents/autonomous_next/top50_raw_55899537.py"
    best = ROOT / "agents/top50_distilled/top50_observable_portfolio.py"
    jobs = [(str(candidate), str(best), seed, seat) for seed in args.seeds for seat in (0,1)]
    rows = []
    with ProcessPoolExecutor(max_workers=max(1,args.workers)) as pool:
        for i,row in enumerate(pool.map(run,jobs),1):
            rows.append(row); print(f"{i}/{len(jobs)} seed={row['seed']} seat={row['seat']}",flush=True)
    valid=[r for r in rows if not r.get('error')]; adv=[r['advantage'] for r in valid]
    by_seed={}
    for r in valid: by_seed.setdefault(r['seed'],[]).append(r['advantage'])
    paired=[statistics.fmean(v) for _,v in sorted(by_seed.items()) if len(v)==2]
    summary={"games":len(valid),"seeds":len(paired),"wins":sum(x>0 for x in adv),"losses":sum(x<0 for x in adv),"ties":sum(x==0 for x in adv),"average_candidate_money":statistics.fmean(r['candidate_money'] for r in valid),"average_best_money":statistics.fmean(r['best_money'] for r in valid),"average_advantage":statistics.fmean(adv),"median_advantage":statistics.median(adv),"paired_average_advantage":statistics.fmean(paired) if paired else None,"paired_median_advantage":statistics.median(paired) if paired else None,"p10_advantage":sorted(adv)[max(0,int(len(adv)*.10)-1)] if adv else None,"p5_advantage":sorted(adv)[max(0,int(len(adv)*.05)-1)] if adv else None,"variance_advantage":statistics.pvariance(adv) if len(adv)>1 else 0.0,"errors":[r for r in rows if r.get('error')]}
    OUT.write_text(json.dumps({"schema_version":1,"seed_panel":args.seeds,"candidate":str(candidate),"best":str(best),"rows":rows,"summary":summary},indent=2,sort_keys=True)+"\n")
    print(OUT); print(summary)


if __name__ == "__main__": main()
