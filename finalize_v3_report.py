"""Consolidate V3 evidence, negative promotion decision, and final report."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics

from run_super_replay_search import _percentile


ROOT=Path(__file__).resolve().parent
REPORT=ROOT/"experiments/super_replay_backbone_v3_report.md"
LOG=ROOT/"experiments/log.md"
V2_PATH="agents/super_replay_v2/super_backbone_v2.py"
BRANCH_PATH="agents/super_replay_v3/v3_branch_opponent_bank_644.py"


def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


def paired(path,candidate):
    d=json.loads((ROOT/path).read_text());by=defaultdict(dict)
    for row in d["games"]:
        key=(row["group"],row["opponent"],row["seed"],row["seat"],row["shop_mode"]);by[key][row["candidate"]]=row
    rows=[]
    for key,pair in by.items():
        if "submission/main.py" not in pair or candidate not in pair:continue
        base,other=pair["submission/main.py"],pair[candidate]
        state=base.get("checkpoints",{}).get("160") or other.get("checkpoints",{}).get("160")
        rows.append({"key":key,"delta_money":other["money"]-base["money"],
            "delta_advantage":other["advantage"]-base["advantage"],"base":base,"candidate":other,
            "activated":bool(state and state["opponent_money"]<=644)})
    deltas=[r["delta_money"] for r in rows];advantages=[r["candidate"]["advantage"] for r in rows]
    active=[r["delta_money"] for r in rows if r["activated"]];inactive=[r["delta_money"] for r in rows if not r["activated"]]
    by_group={}
    for group in sorted({r["key"][0] for r in rows}):
        values=[r["delta_money"] for r in rows if r["key"][0]==group]
        by_group[group]={"games":len(values),"wins":sum(v>0 for v in values),"losses":sum(v<0 for v in values),
            "ties":sum(v==0 for v in values),"average_delta_money":statistics.fmean(values)}
    return {"games":len(rows),"wins":sum(v>0 for v in deltas),"losses":sum(v<0 for v in deltas),"ties":sum(v==0 for v in deltas),
        "decisive_win_rate":sum(v>0 for v in deltas)/max(1,sum(v!=0 for v in deltas)),
        "average_delta_money":statistics.fmean(deltas),"median_delta_money":statistics.median(deltas),
        "activation_count":len(active),"activation_rate":len(active)/len(rows),
        "activated_average_delta_money":statistics.fmean(active) if active else None,
        "inactive_average_delta_money":statistics.fmean(inactive) if inactive else None,
        "candidate_p25_advantage":_percentile(advantages,.25),"candidate_p10_advantage":_percentile(advantages,.10),
        "candidate_p5_advantage":_percentile(advantages,.05),"candidate_worst_advantage":min(advantages),
        "offline_oracle_average_gain":statistics.fmean(max(0,v) for v in deltas),"by_group":by_group}


def enrich_failures():
    path=ROOT/"experiments/v3_v2_failure_clusters.json";d=json.loads(path.read_text());episodes=d["episodes"]
    ordered=sorted(episodes,key=lambda r:r["margin"]);n=len(ordered)
    buckets={
        "bottom_10_percent":ordered[:max(1,round(n*.10))],
        "bottom_25_percent":ordered[:max(1,round(n*.25))],
        "normal_middle_50_percent":ordered[round(n*.25):round(n*.75)],
        "high_money_top_10_percent":sorted(episodes,key=lambda r:r["final_money"],reverse=True)[:max(1,round(n*.10))],
        "losses":[r for r in episodes if r["result"]=="loss"],
    }
    d["v3_outcome_buckets"]={name:{"games":len(rows),"average_money":statistics.fmean(r["final_money"] for r in rows),
        "average_margin":statistics.fmean(r["margin"] for r in rows),"average_repairs":statistics.fmean(r["route_divergence_count"] for r in rows),
        "average_productive_peak":statistics.fmean(r["economy"]["max_productive_tiles"] for r in rows),
        "average_inventory_value":statistics.fmean(r["final_inventory_value"] for r in rows)} for name,rows in buckets.items()}
    clusters=[]
    for row in buckets["losses"]:
        if row["first_large_divergence_step"] is not None and row["first_large_divergence_step"]>=648:
            cluster="endgame_economic_disadvantage"
        elif row["first_large_divergence_step"] is not None and row["first_large_divergence_step"]>=450:
            cluster="market_realization_deficit"
        elif row["route_divergence_count"]:
            cluster="route_drift"
        else:cluster="unknown"
        clusters.append({"episode_id":row["episode_id"],"opponent":row["opponent"],"cluster":cluster,
            "first_meaningful_divergence_step":row["first_large_divergence_step"],"margin":row["margin"],
            "physical_production_intact":row["economy"]["max_productive_tiles"]>=73,
            "route_repairs":row["route_divergence_count"],"stranded_value":row["final_inventory_value"]})
    d["failure_clusters"]={"episodes":clusters,"counts":dict(Counter(r["cluster"] for r in clusters)),
        "interpretation":"All six losses retained physical scale and zero stranded value; clusters describe economic timing, not proven causal repair targets."}
    path.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
    return d


def main():
    corpus=json.loads((ROOT/"experiments/v3_top10_corpus_manifest.json").read_text())
    stability=json.loads((ROOT/"experiments/v3_route_stability.json").read_text())
    families=json.loads((ROOT/"experiments/v3_route_families.json").read_text())
    failures=enrich_failures();raw=json.loads((ROOT/"experiments/v3_candidate_search.json").read_text())
    serious=json.loads((ROOT/"experiments/v3_raw_serious_nazmus.json").read_text())
    branches=json.loads((ROOT/"experiments/v3_branch_candidates.json").read_text())
    oracle=json.loads((ROOT/"experiments/v3_oracle_analysis.json").read_text())
    selection=json.loads((ROOT/"experiments/v3_selection_results.json").read_text())
    final=json.loads((ROOT/"experiments/v3_final_validation.json").read_text())
    selection_pair=paired("experiments/v3_selection_results.json",BRANCH_PATH)
    final_pair=paired("experiments/v3_final_validation.json",BRANCH_PATH)
    oracle["selection_paired_oracle"]={"routes":["V2","branch"],"average_gain_vs_v2":selection_pair["offline_oracle_average_gain"]}
    oracle["final_paired_oracle"]={"routes":["V2","branch"],"average_gain_vs_v2":final_pair["offline_oracle_average_gain"]}
    oracle["headroom_conclusion"]="Compatible-route oracle gain is small; replay selection is near saturation for the mined family."
    (ROOT/"experiments/v3_oracle_analysis.json").write_text(json.dumps(oracle,indent=2,sort_keys=True)+"\n")
    branch_artifact={**branches,"selection_paired":selection_pair,"final_paired":final_pair,
        "promotion_decision":"rejected","reasons":["negative paired own-money mean in selection and final",
        "final decisive win rate below 60%","natural-RNG paired delta negative","activated predicate regressed on unseen states"]}
    (ROOT/"experiments/v3_branch_candidates.json").write_text(json.dumps(branch_artifact,indent=2,sort_keys=True)+"\n")

    class_counts=Counter(r["classification"] for r in stability["submissions"])
    raw_rows=[]
    for path,row in sorted(raw["summary"].items(),key=lambda x:x[1]["average_advantage"],reverse=True):
        raw_rows.append(f"| {Path(path).stem} | {row['wins']}/{row['losses']}/{row['ties']} | {row['average_money']:,.0f} | {row['average_advantage']:+,.0f} | {row['p10']:+,.0f} | {row['p5']:+,.0f} | {row['livestock_losses']} |")
    stable_rows=[]
    for row in stability["submissions"]:
        stable_rows.append(f"| {row['rank']} | {row['team_name']} | `{row['submission_id']}` | {row['appearances']} | {row['classification']} | {row['average_final_money']:,.0f} |")
    failure_rows=[]
    for row in failures["failure_clusters"]["episodes"]:
        failure_rows.append(f"| {row['episode_id']} | {row['opponent']} | {row['cluster']} | {row['first_meaningful_divergence_step']} | {row['margin']:+,.0f} |")
    sel=selection["summary"][BRANCH_PATH];fin=final["summary"][BRANCH_PATH]
    v2s=selection["summary"]["submission/main.py"];v2f=final["summary"]["submission/main.py"]
    best=branch_artifact["candidates"][0];dev_oracle=oracle["offline_route_oracle"]
    report=f"""# Super Replay Backbone V3 research report

## Decision

V3 was **not promoted**. Frozen V2 remains the research best. The one-branch
policy improved opponent-relative results, but failed the causal promotion gate:
paired own money was {selection_pair['average_delta_money']:+.1f} in selection
and {final_pair['average_delta_money']:+.1f} on final holdout. Final paired
W/L/T was {final_pair['wins']}/{final_pair['losses']}/{final_pair['ties']}, only
{final_pair['decisive_win_rate']:.1%} decisive wins.

`submission/main.py` was not modified and nothing was submitted to Kaggle.

## 1–4. Corpus, versions, stability, families

The current Top-10 snapshot contains 10 active submission versions and 126
valid unique replays: 71 development, 24 selection, and 31 final holdout.
Those splits were fixed before action mining. Development contributed 82
deduplicated elite appearances. All 71 development replays had exact bank
reconstruction with zero unexplained mismatches.

Stability distribution: {dict(class_counts)}. Three structural families were
found: a seven-route JALKARNA-like family, a rank-1/Nazmus family, and the
distinct researchstudio route.

| Rank | Team | Submission | Dev appearances | Stability | Avg source money |
|---:|---|---:|---:|---|---:|
{chr(10).join(stable_rows)}

## 5. Complete-route screen

| Route | W/L/T | Avg money | Avg advantage | P10 | P5 | Livestock losses |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(raw_rows)}

Nazmus (`55445174`) was the strongest complete route: the serious paired set
showed 18/6 money wins against V2 and +25,436 average paired money. It was
rejected because two cows actually escaped at step 671 in two paired conditions
(four loss flags across fixed/natural records). Rank 1 was also unsafe. No
safe complete route robustly dominated V2.

## 6. Strongest coherent tail

The best compatible replacement was the Furious Monk tail at step 160
(`v3_tail_55474695_160`), entry distance 0.006. Its cheap screen was 12/4 with
+911 average advantage and zero losses. Direct paired money was only -77 over
16 states; in the larger development counterfactual set it was +5. The adjacent
step-240 version was nearly identical (+908); the Jason step-336 tail was
weaker (+236). Incompatible families were never spliced.

## 7. V2 failure clusters

Deployed V2 submission `55473991` had 76 valid public episodes: 70 wins and six
losses, with zero financial reconstruction mismatches. Land, hires, livestock,
crop cohorts, productive scale, worker routing, and end inventory remained
intact. Four of six losses developed a capital shortfall after preserved
physical production. The repeated weakness remains realized market revenue.

| Episode | Opponent | Cluster | First divergence | Margin |
|---:|---|---|---:|---:|
{chr(10).join(failure_rows)}

## 8–10. Branch point, predicate, activation

Only synchronization-compatible step 160 was promoted to branch testing. The
best development rule was:

```text
if opponent_bank_at_step_160 <= 644:
    choose Furious-Monk tail
else:
    remain on V2
```

Development activation was {best['activation_rate']:.1%} ({best['activations']}/{best['games']})
with {best['average_paired_gain_vs_v2']:+.1f} average gain. Selection activation
was {selection_pair['activation_rate']:.1%}; final activation was
{final_pair['activation_rate']:.1%}. Crucially, activated unseen states lost
{selection_pair['activated_average_delta_money']:.1f} coins in selection and
{final_pair['activated_average_delta_money']:.1f} in final. The observational
threshold did not generalize causally.

## 11–18. Baseline, branch, selection, and final results

| Tier / agent | Games | W/L/T vs opponent | Avg money | Avg advantage | P10 | P5 |
|---|---:|---:|---:|---:|---:|---:|
| Selection V2 | {v2s['games']} | {v2s['wins']}/{v2s['losses']}/{v2s['ties']} | {v2s['average_money']:,.0f} | {v2s['average_advantage']:+,.0f} | {v2s['p10']:+,.0f} | {v2s['p5']:+,.0f} |
| Selection branch | {sel['games']} | {sel['wins']}/{sel['losses']}/{sel['ties']} | {sel['average_money']:,.0f} | {sel['average_advantage']:+,.0f} | {sel['p10']:+,.0f} | {sel['p5']:+,.0f} |
| Final V2 | {v2f['games']} | {v2f['wins']}/{v2f['losses']}/{v2f['ties']} | {v2f['average_money']:,.0f} | {v2f['average_advantage']:+,.0f} | {v2f['p10']:+,.0f} | {v2f['p5']:+,.0f} |
| Final branch | {fin['games']} | {fin['wins']}/{fin['losses']}/{fin['ties']} | {fin['average_money']:,.0f} | {fin['average_advantage']:+,.0f} | {fin['p10']:+,.0f} | {fin['p5']:+,.0f} |

Final natural-RNG paired own-money delta was
{final_pair['by_group']['final_v2_natural']['average_delta_money']:+.1f}; fixed
RNG was {final_pair['by_group']['final_v2_fixed']['average_delta_money']:+.1f};
elite traces were {final_pair['by_group']['final_elite_trace']['average_delta_money']:+.1f}.

## 14 and 25. Oracle and remaining headroom

On 24 development counterfactual states:

- fixed V2 gain: 0 by definition;
- always-tail gain: {oracle['single_fixed_tail']['average_paired_gain_vs_v2']:+.1f};
- best simple branch gain: {oracle['best_simple_branch']['average_paired_gain_vs_v2']:+.1f};
- perfect future-aware route oracle: {dev_oracle['average_gain_vs_v2']:+.1f}.

The final two-route oracle gained only
{oracle['final_paired_oracle']['average_gain_vs_v2']:+.1f}. This is too little
headroom to justify a learned selector: the compatible replay family is near
its route-selection ceiling.

## 19–22. Tail, safety, and fidelity

Final branch P10 was {fin['p10']:+,.0f} versus V2 {v2f['p10']:+,.0f}; P5 was
{fin['p5']:+,.0f} versus {v2f['p5']:+,.0f}. These opponent-relative tail gains
did not compensate for negative paired own money. Both finalists had zero
runtime failures, semantic failures, livestock losses, meaningful stranding,
or fallback. Final route fidelity was {fin['route_fidelity']:.6%} for both.

## 23–26. Promotion and next architecture decision

- V3 promoted: **No**.
- Research best remains `{V2_PATH}` SHA `{sha(V2_PATH)}`.
- Candidate branch SHA: `{sha(BRANCH_PATH)}` (research only, rejected).
- Remaining compatible replay-branch headroom: approximately 35–85 coins per
  game in these counterfactual pools—noise-level relative to V2 income.
- V4 should **not** add more replay branches and should **not** begin RL or a
  learned route selector: the oracle is not large enough. Continue replay
  mining only when a genuinely new, safe coherent family appears; otherwise
  study a narrowly bounded learned residual/market correction with a separate
  causal gate, not route selection and not policy-from-scratch RL.

## Final promotion checklist

- Positive paired mean: FAIL
- >=60% decisive paired wins: FAIL
- Positive natural RNG: FAIL
- Selection and final positive own-money delta: FAIL
- P10/P5 non-regression: PASS (opponent-relative)
- Runtime/semantic/livestock/stranding safety: PASS
- Low complexity: PASS (one branch)

The evidence does not justify replacing V2.
"""
    REPORT.write_text(report)
    marker="## Super Replay Backbone V3"
    log=LOG.read_text()
    if marker not in log:
        LOG.write_text(log.rstrip()+f"\n\n{marker}\n\n"
            f"- **Corpus:** current Top-10, 10 submission versions, 126 valid unique replays; split 71 development / 24 selection / 31 final before action mining; zero development financial mismatches.\n"
            f"- **Routes:** 10 complete routes, 3 structural families. Nazmus was strongest but unsafe (two actual cow escapes in two conditions). Best safe tail was Furious Monk from step 160.\n"
            f"- **Branch:** step 160, opponent bank <= 644 selects the compatible tail. Development oracle +{dev_oracle['average_gain_vs_v2']:.0f}; branch selection/final paired own-money deltas {selection_pair['average_delta_money']:+.1f}/{final_pair['average_delta_money']:+.1f}.\n"
            f"- **Final:** branch paired W/L/T {final_pair['wins']}/{final_pair['losses']}/{final_pair['ties']}; zero safety failures, but promotion gate failed. V2 remains best.\n"
            f"- **Deployment:** `submission/main.py` unchanged; no Kaggle submission or upload performed.\n")
    print(REPORT)


if __name__=="__main__":main()
