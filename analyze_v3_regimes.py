"""Build causal route-regime tables and minimal branch candidates."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import statistics

from run_super_replay_search import _percentile


ROOT=Path(__file__).resolve().parent
RUNS=ROOT/"experiments/v3_route_regime_runs.json"
PERFORMANCE=ROOT/"experiments/v3_route_regime_performance.json"
BRANCHES=ROOT/"experiments/v3_branch_candidates.json"
ORACLE=ROOT/"experiments/v3_oracle_analysis.json"
V2="submission/main.py"
TAIL="agents/super_replay_v3/v3_tail_55474695_160.py"


def key(row):return (row["group"],row["opponent"],row["seed"],row["seat"],row["shop_mode"])


def features(state):
    output={"bank":state["money"],"opponent_bank":state["opponent_money"]}
    for item,value in state["market_prices"].items():output[f"price_{item.lower()}"]=value
    for item,value in state["market_inventory"].items():output[f"inventory_{item.lower()}"]=value
    return output


def summary(rows,selector):
    chosen=[];advantages=[];money=[];gains=[]
    for row in rows:
        use=selector(row["features"]);selected=row["tail"] if use else row["v2"]
        chosen.append(use);money.append(selected["money"]);advantages.append(selected["advantage"])
        gains.append(selected["money"]-row["v2"]["money"])
    return {"games":len(rows),"activations":sum(chosen),"activation_rate":sum(chosen)/len(rows),
        "average_money":statistics.fmean(money),"average_advantage":statistics.fmean(advantages),
        "average_paired_gain_vs_v2":statistics.fmean(gains),"wins":sum(x>0 for x in advantages),
        "losses":sum(x<0 for x in advantages),"p25_advantage":_percentile(advantages,.25),
        "p10_advantage":_percentile(advantages,.10),"p5_advantage":_percentile(advantages,.05),
        "worst_advantage":min(advantages),"activated_average_gain":statistics.fmean([g for g,c in zip(gains,chosen) if c]) if any(chosen) else None,
        "inactive_average_gain":statistics.fmean([g for g,c in zip(gains,chosen) if not c]) if not all(chosen) else None}


def main():
    games=json.loads(RUNS.read_text())["games"];paired=defaultdict(dict)
    for row in games:paired[key(row)][row["candidate"]]=row
    rows=[]
    for condition,pair in paired.items():
        if V2 not in pair or TAIL not in pair:continue
        base,tail=pair[V2],pair[TAIL];state=base.get("checkpoints",{}).get("160") or tail.get("checkpoints",{}).get("160")
        rows.append({"condition":condition,"features":features(state),"v2":base,"tail":tail,"tail_gain":tail["money"]-base["money"]})

    candidates=[]
    for feature in sorted(rows[0]["features"]):
        values=sorted({row["features"][feature] for row in rows})
        thresholds=[(a+b)/2 for a,b in zip(values,values[1:])]
        for threshold in thresholds:
            for operator in ("<=",">="):
                predicate=(lambda f,feature=feature,threshold=threshold,operator=operator: f[feature]<=threshold if operator=="<=" else f[feature]>=threshold)
                result=summary(rows,predicate)
                if 4<=result["activations"]<=len(rows)-4:
                    candidates.append({"feature":feature,"operator":operator,"threshold":threshold,"complexity":1,**result})
    candidates.sort(key=lambda r:(r["average_paired_gain_vs_v2"],r["p10_advantage"],-r["activations"]),reverse=True)
    # Preserve at most ten genuinely different one-threshold hypotheses.
    selected=[];seen=set()
    for row in candidates:
        signature=(row["feature"],row["operator"])
        if signature in seen:continue
        seen.add(signature);selected.append(row)
        if len(selected)==10:break
    baseline=summary(rows,lambda f:False);always_tail=summary(rows,lambda f:True);oracle=summary(rows,lambda f:False)
    oracle_money=[max(row["v2"]["money"],row["tail"]["money"]) for row in rows]
    oracle_adv=[(row["tail"] if row["tail"]["money"]>row["v2"]["money"] else row["v2"])["advantage"] for row in rows]
    oracle={"games":len(rows),"average_money":statistics.fmean(oracle_money),
        "average_gain_vs_v2":statistics.fmean(max(0,row["tail_gain"]) for row in rows),
        "tail_chosen":sum(row["tail_gain"]>0 for row in rows),"p10_advantage":_percentile(oracle_adv,.10),
        "p5_advantage":_percentile(oracle_adv,.05),"worst_advantage":min(oracle_adv)}
    regimes=[]
    for feature in sorted(rows[0]["features"]):
        values=[row["features"][feature] for row in rows];median=statistics.median(values)
        for label,predicate in (("low",lambda x,m=median:x<=m),("high",lambda x,m=median:x>m)):
            subset=[r for r in rows if predicate(r["features"][feature])]
            if subset:regimes.append({"feature":feature,"bucket":label,"threshold":median,"sample_count":len(subset),
                "v2_average_money":statistics.fmean(r["v2"]["money"] for r in subset),
                "tail_average_money":statistics.fmean(r["tail"]["money"] for r in subset),
                "tail_average_gain":statistics.fmean(r["tail_gain"] for r in subset),
                "tail_win_share":sum(r["tail_gain"]>0 for r in subset)/len(subset),
                "tail_gain_p10":_percentile([r["tail_gain"] for r in subset],.10)})
    PERFORMANCE.write_text(json.dumps({"schema_version":1,"branch_step":160,"paired_states":len(rows),
        "route_a":V2,"route_b":TAIL,"regimes":regimes},indent=2,sort_keys=True)+"\n")
    BRANCHES.write_text(json.dumps({"schema_version":1,"search":"single observable threshold only; minimum 4 activations/inactivations",
        "baseline":baseline,"always_tail":always_tail,"candidates":selected,"all_candidate_count":len(candidates)},indent=2,sort_keys=True)+"\n")
    ORACLE.write_text(json.dumps({"schema_version":1,"development_counterfactual_states":len(rows),"single_fixed_v2":baseline,
        "single_fixed_tail":always_tail,"best_simple_branch":selected[0] if selected else None,"offline_route_oracle":oracle,
        "interpretation":"Oracle uses future outcome and is an upper bound, never an agent policy."},indent=2,sort_keys=True)+"\n")
    print(json.dumps({"pairs":len(rows),"baseline":baseline,"tail":always_tail,"best":selected[0] if selected else None,"oracle":oracle},indent=2))


if __name__=="__main__":main()
