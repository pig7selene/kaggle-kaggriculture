"""Transition-ledger attribution for the raw route challenger."""

from __future__ import annotations

from collections import Counter
import json
import statistics
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from mine_top50_strategies import _economic_timeline

ROOT = Path(__file__).resolve().parent
BASELINE = ROOT / "agents/top50_distilled/top50_observable_portfolio.py"
CANDIDATE = ROOT / "agents/autonomous_next/top50_raw_55899537.py"
OUT = ROOT / "experiments" / "autonomous_route_economics.json"


def _run(path, seed, seat):
    candidate = run_path(str(path))["agent"]
    rival = run_path(str(BASELINE))["agent"]
    pair = [rival, rival]
    pair[seat] = candidate
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    env.run(pair)
    replay = env.toJSON()
    timeline, reconciliation = _economic_timeline(replay, seat)
    final = replay["steps"][-1]
    revenue = Counter(); sales = Counter(); harvest = Counter(); planted = Counter()
    costs = Counter()
    for row in timeline:
        revenue.update(row["sale_revenue"]); sales.update(row["sale_quantity"])
        harvest.update(row["harvest_quantity"]); planted.update(row["plant_quantity"])
        costs["seeds"] += sum(row["seed_spend"].values())
        costs["animals"] += sum(row["animal_spend"].values())
        costs["feed_and_products"] += sum(row["product_spend"].values())
        costs["hands"] += row["labor_spend"]; costs["land"] += row["land_spend"]
    return {"path": str(path), "seed": seed, "seat": seat, "money": float(final[seat]["reward"]), "opponent_money": float(final[1-seat]["reward"]), "revenue": dict(revenue), "sales": dict(sales), "harvest": dict(harvest), "planted": dict(planted), "costs": dict(costs), "reconciliation_events": len(reconciliation)}


def _mean(rows, key):
    keys = sorted({k for row in rows for k in row[key]})
    return {k: statistics.fmean(row[key].get(k, 0) for row in rows) for k in keys}


def main():
    rows = []
    for seed in range(17100, 17104):
        for seat in (0, 1):
            rows.append(_run(BASELINE, seed, seat)); rows.append(_run(CANDIDATE, seed, seat))
            print(seed, seat, flush=True)
    base = [r for r in rows if r["path"] == str(BASELINE)]
    cand = [r for r in rows if r["path"] == str(CANDIDATE)]
    delta = {"money": statistics.fmean(r["money"] for r in cand) - statistics.fmean(r["money"] for r in base), "opponent_money": statistics.fmean(r["opponent_money"] for r in cand) - statistics.fmean(r["opponent_money"] for r in base), "revenue": {k: statistics.fmean(r["revenue"].get(k,0) for r in cand) - statistics.fmean(r["revenue"].get(k,0) for r in base) for k in sorted(set(_mean(cand,'revenue'))|set(_mean(base,'revenue')))}, "costs": {k: statistics.fmean(r["costs"].get(k,0) for r in cand) - statistics.fmean(r["costs"].get(k,0) for r in base) for k in sorted(set(_mean(cand,'costs'))|set(_mean(base,'costs')))}, "harvest": {k: statistics.fmean(r["harvest"].get(k,0) for r in cand) - statistics.fmean(r["harvest"].get(k,0) for r in base) for k in sorted(set(_mean(cand,'harvest'))|set(_mean(base,'harvest')))}}
    payload = {"schema_version": 1, "design": "four fresh seeds, both seats, complete route vs frozen portfolio", "baseline": str(BASELINE), "candidate": str(CANDIDATE), "rows": rows, "summary": {"baseline": {"average_money": statistics.fmean(r["money"] for r in base), "average_revenue": _mean(base,'revenue'), "average_costs": _mean(base,'costs'), "average_harvest": _mean(base,'harvest')}, "candidate": {"average_money": statistics.fmean(r["money"] for r in cand), "average_revenue": _mean(cand,'revenue'), "average_costs": _mean(cand,'costs'), "average_harvest": _mean(cand,'harvest')}, "delta_candidate_minus_baseline": delta}}
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True)+"\n")
    print(OUT)


if __name__ == '__main__': main()
