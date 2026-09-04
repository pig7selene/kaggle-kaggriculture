"""Economic attribution on the same games used for raw-route H2H confirmation."""

from __future__ import annotations

from collections import Counter
import json
import statistics
from pathlib import Path
from runpy import run_path

from kaggle_environments import make
from mine_top50_strategies import _economic_timeline

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "agents/top50_distilled/top50_observable_portfolio.py"
CAND = ROOT / "agents/autonomous_next/top50_raw_55899537.py"
OUT = ROOT / "experiments/autonomous_raw_h2h_economics.json"


def _run(seed, seat):
    c = run_path(str(CAND))["agent"]
    b = run_path(str(BASE))["agent"]
    pair = [b, b]; pair[seat] = c
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    env.run(pair)
    replay = env.toJSON()
    rows = []
    for player in (0, 1):
        timeline, reconciliation = _economic_timeline(replay, player)
        rev = Counter(); qty = Counter(); harvest = Counter(); costs = Counter()
        for row in timeline:
            rev.update(row["sale_revenue"]); qty.update(row["sale_quantity"]); harvest.update(row["harvest_quantity"])
            costs["seeds"] += sum(row["seed_spend"].values()); costs["animals"] += sum(row["animal_spend"].values()); costs["feed"] += sum(row["product_spend"].values()); costs["hands"] += row["labor_spend"]; costs["land"] += row["land_spend"]
        rows.append({"player": player, "role": "candidate" if player == seat else "best", "money": float(replay["steps"][-1][player]["reward"]), "revenue": dict(rev), "quantity": dict(qty), "harvest": dict(harvest), "costs": dict(costs), "reconciliation_events": len(reconciliation)})
    return {"seed": seed, "candidate_seat": seat, "players": rows}


def _mean(rows, field):
    keys = sorted({k for row in rows for k in row[field]})
    return {k: statistics.fmean(row[field].get(k, 0) for row in rows) for k in keys}


def main():
    games = [_run(seed, seat) for seed in range(17200, 17204) for seat in (0, 1)]
    c = [next(p for p in g["players"] if p["role"] == "candidate") for g in games]
    b = [next(p for p in g["players"] if p["role"] == "best") for g in games]
    delta = {"money": statistics.fmean(x["money"] for x in c) - statistics.fmean(x["money"] for x in b), "revenue": {k: statistics.fmean(x["revenue"].get(k,0) for x in c) - statistics.fmean(x["revenue"].get(k,0) for x in b) for k in sorted(set(_mean(c,'revenue'))|set(_mean(b,'revenue')))}, "costs": {k: statistics.fmean(x["costs"].get(k,0) for x in c) - statistics.fmean(x["costs"].get(k,0) for x in b) for k in sorted(set(_mean(c,'costs'))|set(_mean(b,'costs')))}, "harvest": {k: statistics.fmean(x["harvest"].get(k,0) for x in c) - statistics.fmean(x["harvest"].get(k,0) for x in b) for k in sorted(set(_mean(c,'harvest'))|set(_mean(b,'harvest')))}}
    payload={"schema_version":1,"design":"four fresh seeds, both seats, candidate and frozen best in the same environment","games":games,"summary":{"candidate":{"average_money":statistics.fmean(x['money'] for x in c),"average_revenue":_mean(c,'revenue'),"average_costs":_mean(c,'costs'),"average_harvest":_mean(c,'harvest')},"best":{"average_money":statistics.fmean(x['money'] for x in b),"average_revenue":_mean(b,'revenue'),"average_costs":_mean(b,'costs'),"average_harvest":_mean(b,'harvest')},"delta_candidate_minus_best":delta}}
    OUT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    print(OUT)


if __name__=='__main__': main()
