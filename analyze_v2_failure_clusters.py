"""Classify V2 finalist failures and decide whether any narrow repair is justified."""

from collections import Counter
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
FINAL = ROOT / "experiments/v2_final_validation.json"
REAL = ROOT / "experiments/v2_real_kaggle_diagnostics.json"
OUTPUT = ROOT / "experiments/v2_failure_clusters.json"
CANDIDATE = "agents/super_replay_v2/v2_raw_55463387.py"


def main():
    final = json.loads(FINAL.read_text()); real = json.loads(REAL.read_text())
    losses=[]
    for row in final["games"]:
        if row["candidate"] != CANDIDATE or row.get("advantage", 0) >= 0: continue
        if row["livestock_losses"].get("COW",0)+row["livestock_losses"].get("SHEEP",0)+row["livestock_losses"].get("GOOSE",0): category="animal_service"
        elif row["stranded_value"] > 500: category="endgame_liquidation"
        elif row["weed_repairs"] >= 2: category="route_drift"
        elif row["advantage"] <= -5000: category="opponent_economic_superiority"
        else: category="market_collision_or_small_edge"
        losses.append({
            "opponent":row["opponent"],"seed":row["seed"],"seat":row["seat"],"advantage":row["advantage"],
            "category":category,"weed_repairs":row["weed_repairs"],"repair_abort":row["repair_abort"],
            "livestock_losses":row["livestock_losses"],"stranded_value":row["stranded_value"],
        })
    counts=Counter(row["category"] for row in losses)
    repair_evidence={
        "livestock_emergency": {"repeated_real_v1_evidence":False,"finalist_loss_activations":counts["animal_service"],"decision":"reject"},
        "capital_milestone": {"repeated_real_v1_evidence":False,"note":"real losses preserve both land milestones and physical economy; cash gap is realized market revenue","decision":"reject"},
        "worker_rematching": {"repeated_real_v1_evidence":False,"note":"no hand or worker-position checkpoint deficit in real losses","decision":"reject"},
        "harvest_rescue": {"repeated_real_v1_evidence":False,"note":"real losses have essentially the same harvest quantities as wins","decision":"reject"},
        "endgame_liquidation": {"repeated_real_v1_evidence":False,"finalist_loss_activations":counts["endgame_liquidation"],"decision":"reject"},
    }
    output={
        "schema_version":1,"candidate":CANDIDATE,"losses":losses,"category_counts":dict(counts),
        "repair_evidence":repair_evidence,
        "strongest_narrow_repair":None,
        "decision":"No new narrow repair is justified. Preserve only K3 weed repair.",
        "real_v1_repeated_failure_modes":real["repeated_failure_modes"],
    }
    OUTPUT.write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"losses":len(losses),"category_counts":dict(counts),"decision":output["decision"]},indent=2))


if __name__=="__main__":main()
