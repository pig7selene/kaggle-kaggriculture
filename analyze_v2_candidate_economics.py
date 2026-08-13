"""Exact paired economic attribution: V2 complete route versus V1."""

from collections import Counter
import json
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from analyze_top_player_replays import _transition_ledger
from run_epic_experiments import _independent_shop_schedule, _run_with_fixed_shops


ROOT = Path(__file__).resolve().parent
CANDIDATE = "agents/super_replay_v2/v2_raw_55463387.py"
BASELINE = "agents/super_replay/super_backbone_v1.py"
OUTPUT = ROOT / "experiments/v2_candidate_economics.json"


def _run(seed, seat):
    candidate = run_path(str(ROOT / CANDIDATE))["agent"]
    baseline = run_path(str(ROOT / BASELINE))["agent"]
    pair = [baseline, baseline]; pair[seat] = candidate
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=True)
    _run_with_fixed_shops(env, pair, _independent_shop_schedule(seed))
    replay = env.toJSON()
    totals = [{"revenue": Counter(), "harvests": Counter(), "seed": 0, "feed": 0, "animals": 0, "land": 0, "labor": 0} for _ in range(2)]
    mismatches = []
    for index in range(1, 720):
        ledgers, errors = _transition_ledger(replay["steps"][index-1], replay["steps"][index], replay.get("configuration", {}))
        mismatches.extend({"step": index, **error} for error in errors)
        for player, ledger in enumerate(ledgers):
            row = totals[player]; row["revenue"].update(ledger["sale_revenue"]); row["harvests"].update(ledger["harvest_quantity"])
            row["seed"] += sum(ledger["seed_spend"].values()); row["feed"] += sum(ledger["product_spend"].values())
            row["animals"] += sum(ledger["animal_spend"].values()); row["land"] += ledger["land_spend"]; row["labor"] += ledger["labor_spend"]
    rows=[]
    for player,row in enumerate(totals):
        rows.append({
            "role": "candidate" if player == seat else "v1", "seat": player,
            "money": float(replay["steps"][-1][player]["reward"]), "revenue": dict(row["revenue"]),
            "total_revenue": sum(row["revenue"].values()), "harvests": dict(row["harvests"]),
            "seed_spend": row["seed"], "feed_spend": row["feed"], "animal_spend": row["animals"],
            "land_spend": row["land"], "labor_spend": row["labor"],
            "total_spend": row["seed"]+row["feed"]+row["animals"]+row["land"]+row["labor"],
        })
    return {"seed": seed, "candidate_seat": seat, "players": rows, "financial_mismatches": mismatches}


def main():
    games=[_run(seed,seat) for seed in range(993500,993508) for seat in (0,1)]
    pairs=[]
    for game in games:
        c=next(x for x in game["players"] if x["role"]=="candidate"); b=next(x for x in game["players"] if x["role"]=="v1")
        pairs.append((c,b))
    products=sorted({p for c,b in pairs for p in set(c["revenue"])|set(b["revenue"])})
    def avg(fn): return sum(fn(c,b) for c,b in pairs)/len(pairs)
    aggregate={
        "games":len(games), "average_final_money_delta":avg(lambda c,b:c["money"]-b["money"]),
        "average_revenue_delta":avg(lambda c,b:c["total_revenue"]-b["total_revenue"]),
        "average_spend_delta":avg(lambda c,b:c["total_spend"]-b["total_spend"]),
        "seed_spend_delta":avg(lambda c,b:c["seed_spend"]-b["seed_spend"]),
        "feed_spend_delta":avg(lambda c,b:c["feed_spend"]-b["feed_spend"]),
        "animal_spend_delta":avg(lambda c,b:c["animal_spend"]-b["animal_spend"]),
        "land_spend_delta":avg(lambda c,b:c["land_spend"]-b["land_spend"]),
        "labor_spend_delta":avg(lambda c,b:c["labor_spend"]-b["labor_spend"]),
        "revenue_delta_by_product":{p:avg(lambda c,b,p=p:c["revenue"].get(p,0)-b["revenue"].get(p,0)) for p in products},
        "harvest_delta_by_product":{p:avg(lambda c,b,p=p:c["harvests"].get(p,0)-b["harvests"].get(p,0)) for p in products},
    }
    OUTPUT.write_text(json.dumps({"schema_version":1,"candidate":CANDIDATE,"baseline":BASELINE,"aggregate":aggregate,"games":games,"financial_mismatch_count":sum(len(g["financial_mismatches"]) for g in games)},indent=2,sort_keys=True)+"\n")
    print(json.dumps(aggregate,indent=2,sort_keys=True))


if __name__=="__main__":main()
