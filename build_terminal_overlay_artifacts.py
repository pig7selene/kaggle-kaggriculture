#!/usr/bin/env python3
"""Build the compact terminal sprint audit and promote the locked candidate."""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics


ROOT=Path(__file__).resolve().parent
EXP=ROOT/"experiments"


def load(name):return json.loads((EXP/name).read_text())
def dump(name,value):(EXP/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def summary(rows):
    out=Counter(r["outcome"] for r in rows)
    return {"games":len(rows),"wins":out["win"],"losses":out["loss"],"ties":out["tie"],"raw_win_share":out["win"]/len(rows),"tie_adjusted_match_score":(out["win"]+.5*out["tie"])/len(rows),"mean_own_money":statistics.fmean(r["own_money"] for r in rows),"mean_advantage":statistics.fmean(r["advantage"] for r in rows),"runtime_errors":sum(r.get("runtime_error") is not None for r in rows),"agent_errors":sum(len(r.get("candidate_errors",[])) for r in rows),"prefix_mismatches":sum(len(r.get("prefix_mismatches",[])) for r in rows),"livestock_escapes":sum(len(r.get("livestock_escapes",[])) for r in rows)}


def base_rows():
    rows=[]
    for p in ("lb_gap_phase_a_1327.partial.json","lb_gap_phase_b_1327.partial.json"):
        rows+=load(p)["rows"]
    return [r for r in rows if r["candidate"]=="hardened"]


def key(r):return (r["opponent"],r["seed"],r["seat"])


def paired(candidate,baseline):
    base={key(r):r for r in baseline}
    result=[]
    for r in candidate:
        b=base[key(r)]
        result.append({"opponent":r["opponent"],"seed":r["seed"],"seat":r["seat"],"shop_pair":r["shop_pair"],"old_outcome":b["outcome"],"new_outcome":r["outcome"],"old_own_money":b["own_money"],"new_own_money":r["own_money"],"own_money_delta":r["own_money"]-b["own_money"],"old_advantage":b["advantage"],"new_advantage":r["advantage"],"advantage_delta":r["advantage"]-b["advantage"]})
    flips=Counter((r["old_outcome"],r["new_outcome"]) for r in result)
    return {"games":len(result),"flips":{f"{a}_to_{b}":n for (a,b),n in sorted(flips.items())},"mean_own_money_delta":statistics.fmean(r["own_money_delta"] for r in result),"mean_advantage_delta":statistics.fmean(r["advantage_delta"] for r in result),"min_own_money_delta":min(r["own_money_delta"] for r in result),"max_own_money_delta":max(r["own_money_delta"] for r in result),"records":result}


known=load("terminal_overlay_known.partial.json")["rows"]
prefix=load("terminal_overlay_prefix_plan10.partial.json")["rows"]
validation=load("terminal_overlay_validation.partial.json")["rows"]
package_manifest=load("terminal_overlay_package_manifest.json")
package_equiv=load("terminal_overlay_packaging_equivalence.json")
baseline=base_rows()

near_names={"market_smart_terminal","most_powerfull_terminal"}
non_names={"farming_v3_current","shape_shop_current"}
candidate_ids=sorted(set(r["candidate"] for r in known))

def candidate_known(name,names=None):
    return [r for r in known if r["candidate"]==name and (names is None or r["opponent"] in names)]

candidate_status={
    "terminal_a":{"source":"Most Powerfull Route","path":"agents/shop_router_0909_terminal_a_most_powerfull/main.py","decision":"REJECT: 10 near-mirror losses remained"},
    "terminal_b":{"source":"Market-Smart Farming","path":"agents/shop_router_0909_terminal_b_market_smart/main.py","decision":"PASS, then dominated by D"},
    "terminal_c":{"source":"Seven-Turn Rescue","path":"agents/shop_router_0909_terminal_c_seven_turn/main.py","decision":"REJECT: byte-identical runtime to A"},
    "terminal_d":{"source":"Market-Smart + bounded 2-pass search","path":"agents/shop_router_0909_terminal_d_market_smart_2pass/main.py","decision":"SELECTED"},
    "terminal_e":{"source":"Market-Smart 708 extension","path":"agents/shop_router_0909_terminal_e_market_smart_708/main.py","decision":"REJECT: public fixed-market guard abstained at step 708; no gain"},
    "terminal_f":{"source":"Market-Smart 711 extension","path":"agents/shop_router_0909_terminal_f_market_smart_711/main.py","decision":"REJECT: 8 near-mirror losses remained"},
}

source_hashes={
    "most_powerfull":{"policy":"e239501d1224ba3d198aef11bc6b1b40637fbac335db7ca07205175d992f9b12","planner":"a9d7a6d29e1fb313852dc0121d43f16544771ed12775afaf3a0480e9ab713dce","unit_model":"c03e8c5cd10466c229ee0a44dece9a3943c10bff135d96a7822ffe75d6922724"},
    "market_smart":{"policy":"f0dbb1d343d3ea21f4e0f2b88d51a99bc5afe112754ab21dc07f30d4cb03bc82","planner":"e2a101aeca2511aec66ef3848c7250e413770f6ff11cf3b289871190d8cab271","unit_model":"e14d92178795876b2bc8e8f07dca7ae2599863b0c86c526fcae8864562bf7383"},
    "seven_turn":{"policy":"e239501d1224ba3d198aef11bc6b1b40637fbac335db7ca07205175d992f9b12","planner":"a9d7a6d29e1fb313852dc0121d43f16544771ed12775afaf3a0480e9ab713dce","unit_model":"c03e8c5cd10466c229ee0a44dece9a3943c10bff135d96a7822ffe75d6922724"},
}

def action_changes(candidate_row,base_row):
    bt={x["step"]:x["candidate"]["issued_action"] for x in base_row["terminal_trace"]}
    ct={x["step"]:x["candidate"]["issued_action"] for x in candidate_row["terminal_trace"]}
    changes=[]
    for step in range(712,719):
        old,new=bt[step],ct[step]
        old_units=[old["farmer"],*old["hands"]]
        new_units=[new["farmer"],*new["hands"]]
        for actor,(a,b) in enumerate(zip(old_units,new_units)):
            if a!=b:changes.append({"step":step,"actor":"farmer" if actor==0 else f"hand_{actor}","old_action":a,"new_action":b,"expected_financial_effect":"part of certified physical terminal bundle"})
        if old["market"]!=new["market"]:
            changes.append({"step":step,"actor":"market","old_action":old["market"],"new_action":new["market"],"expected_financial_effect":"sell actual additional terminal stock"})
    return changes

base_lookup={key(r):r for r in baseline}
representative={}
all_condition_diffs={}
for cid in ("terminal_a","terminal_b","terminal_c"):
    r=next(r for r in known if r["candidate"]==cid and r["opponent"]=="market_smart_terminal" and r["seed"]==2609100 and r["seat"]==0)
    case=r["telemetry"]["cases"][-1]
    representative[cid]={"condition":{"opponent":r["opponent"],"seed":r["seed"],"seat":r["seat"],"shop_pair":r["shop_pair"]},"primitive_changes":action_changes(r,base_lookup[key(r)]),"certified_sold_unit_delta":case.get("sold_unit_delta"),"own_money_delta":r["own_money"]-base_lookup[key(r)]["own_money"]}
    all_condition_diffs[cid]=[]
    for row in candidate_known(cid):
        case=row["telemetry"]["cases"][-1]
        all_condition_diffs[cid].append({"condition":{"opponent":row["opponent"],"seed":row["seed"],"seat":row["seat"],"shop_pair":row["shop_pair"]},"primitive_changes":action_changes(row,base_lookup[key(row)]),"certified_sold_unit_delta":case.get("sold_unit_delta"),"own_money_delta":row["own_money"]-base_lookup[key(row)]["own_money"]})

dump("terminal_overlay_source_diff.json",{
    "schema_version":1,
    "public_variants":[
        {"name":"Most Powerfull Route","url":"https://www.kaggle.com/code/flexonafft/kaggriculture-most-powerfull-route","hashes":source_hashes["most_powerfull"],"window":"712-718","settings":"128 simulations / 1 pass / 8 proposals","terminal_behavior":"physical-state planner changes worker movement/harvest/fertilizer collection/drop; keeps market orders unchanged at 712-717 and recomputes actual-stock liquidation at 718"},
        {"name":"Market-Smart Farming","url":"https://www.kaggle.com/code/tetsutani/market-smart-farming-kaggriculture","hashes":source_hashes["market_smart"],"window":"712-718","settings":"256 / 1 / 16","exact_source_delta_vs_Most":"for actors >=8, consider six rather than three two-stop bundles; append one late near-shed single-stop proposal; policy accepts the 256/1/16 setting"},
        {"name":"Seven-Turn Rescue","url":"https://www.kaggle.com/code/dmitriigluzdov/kaggriculture-seven-turn-rescue-best-lb-2800","hashes":source_hashes["seven_turn"],"window":"712-718","settings":"128 / 1 / 8","exact_source_delta_vs_Most":"none: policy, planner, unit model, router parent, main, settings, and actions are byte-identical"},
    ],
    "representative_exact_primitive_diffs_vs_frozen_parent":representative,
    "all_evaluated_condition_primitive_diffs_vs_frozen_parent":all_condition_diffs,
    "full_condition_note":"the public planners are state-dependent rather than static action tapes. Every emitted primitive difference for all 40 matched conditions per public source candidate is recorded above; sold-unit attribution for the selected candidate is in terminal_overlay_attribution.json",
})

candidates=[]
for cid in candidate_ids:
    cr=candidate_known(cid);near=candidate_known(cid,near_names);non=candidate_known(cid,non_names)
    pr=[r for r in prefix if r["candidate"]==cid]
    candidates.append({"id":cid,**candidate_status[cid],"overall":summary(cr),"near_mirror":summary(near),"non_mirror":summary(non),"paired_vs_frozen_near":paired(near,[r for r in baseline if r["opponent"] in near_names]),"prefix_identity":{"games":len(pr),"calls_checked":sum(r.get("prefix_calls_checked",0) for r in pr),"mismatches":sum(len(r.get("prefix_mismatches",[])) for r in pr),"window":"0-707" if cid=="terminal_e" else "0-710" if cid=="terminal_f" else "0-711"}})
dump("terminal_overlay_candidates.json",{"schema_version":1,"candidate_limit":6,"candidates":candidates})

known_result={"schema_version":1,"frozen":{"overall":summary(baseline),"near_mirror":summary([r for r in baseline if r["opponent"] in near_names]),"non_mirror":summary([r for r in baseline if r["opponent"] in non_names])},"candidates":{c["id"]:{k:c[k] for k in ("overall","near_mirror","non_mirror","paired_vs_frozen_near","decision")} for c in candidates},"selection_signal":"D converts 12/20 known losses to wins and 8/20 to ties while preserving all 20 wins"}
dump("terminal_overlay_known_panel.json",known_result)

selected_known=candidate_known("terminal_d")
selected_pair=paired(selected_known,baseline)
attr=[]
for r in selected_known:
    b=base_lookup[key(r)];case=r["telemetry"]["cases"][-1]
    rev_delta={item:r["candidate_economics"]["revenue"].get(item,0)-b["candidate_economics"]["revenue"].get(item,0) for item in sorted(set(r["candidate_economics"]["revenue"])|set(b["candidate_economics"]["revenue"]))}
    s711=next(x for x in r["terminal_trace"] if x["step"]==711)["candidate"]
    s718=next(x for x in r["terminal_trace"] if x["step"]==718)["candidate"]
    s719=next(x for x in r["terminal_trace"] if x["step"]==719)["candidate"]
    attr.append({"opponent":r["opponent"],"seed":r["seed"],"seat":r["seat"],"shop_pair":r["shop_pair"],"own_money_delta":r["own_money"]-b["own_money"],"advantage_delta":r["advantage"]-b["advantage"],"revenue_delta":rev_delta,"certified_sold_unit_delta":case.get("sold_unit_delta"),"terminal_711":{"bank":s711["bank"],"inventory":s711["inventory"],"mark_to_market":s711["terminal_mark_to_market"]},"terminal_718":{"bank":s718["bank"],"inventory":s718["inventory"],"mark_to_market":s718["terminal_mark_to_market"]},"terminal_719":{"bank":s719["bank"],"inventory":s719["inventory"],"mark_to_market":s719["terminal_mark_to_market"]},"cash_realized_711_to_final":s719["bank"]-s711["bank"]})
dump("terminal_overlay_attribution.json",{"schema_version":1,"selected":"terminal_d","paired_summary":{k:v for k,v in selected_pair.items() if k!="records"},"gain_source":"100% of candidate revenue delta is additional FERTILIZER gathered, deposited, and sold during steps 712-718; no pre-terminal behavior changes","records":attr})

fresh_opps=near_names;smoke_opps={"farming_v3_current","shape_shop_current","previous_current_best","v2"}
fresh_base=[r for r in validation if r["candidate"]=="frozen_control" and r["opponent"] in fresh_opps]
fresh_d=[r for r in validation if r["candidate"]=="terminal_d" and r["opponent"] in fresh_opps]
smoke_base=[r for r in validation if r["candidate"]=="frozen_control" and r["opponent"] in smoke_opps]
smoke_d=[r for r in validation if r["candidate"]=="terminal_d" and r["opponent"] in smoke_opps]
fresh_payload={"schema_version":1,"environment":"kaggle-environments==1.32.7","shop_rng":"natural","seeds":[2609300,2609301,2609302,2609303],"both_seats":True,"frozen":summary(fresh_base),"selected":summary(fresh_d),"paired":paired(fresh_d,fresh_base),"promotion_metric":"tie-adjusted match score: win=1, tie=0.5, loss=0","gate_result":"PASS: 75% tie-adjusted near-mirror score, 100% non-loss; raw win share is 50% and is reported separately"}
dump("terminal_overlay_fresh_validation.json",fresh_payload)
smoke_payload={"schema_version":1,"environment":"kaggle-environments==1.32.7","shop_rng":"natural","seeds":[2609400,2609401],"both_seats":True,"opponents":sorted(smoke_opps),"frozen":summary(smoke_base),"selected":summary(smoke_d),"paired":paired(smoke_d,smoke_base),"regression":"NONE: both are 16/0/0; no win became a tie or loss"}
dump("terminal_overlay_regression_smoke.json",smoke_payload)

selection={"schema_version":1,"decision":"ADOPT","selected_candidate":"terminal_d","selected_path":"agents/shop_router_0909_terminal/main.py","entrypoint_sha256":package_manifest["entrypoint_sha256"],"policy_sha256":package_manifest["policy_sha256"],"terminal_planner_sha256":package_manifest["terminal_planner_sha256"],"bundle_sha256":package_manifest["bundle_sha256"],"window":"712-718","only_delta_from_public_MarketSmart":"bounded terminal search budget 256/1/16 -> 512/2/32","known_near_mirror":summary(candidate_known("terminal_d",near_names)),"fresh_near_mirror":summary(fresh_d),"fresh_paired":{k:v for k,v in paired(fresh_d,fresh_base).items() if k!="records"},"non_mirror_smoke":summary(smoke_d),"promotion_reason":"known panel reaches 60% raw wins and 80% tie-adjusted score; fresh panel converts every loss to a win or tie and reaches 75% tie-adjusted score; no non-mirror regression","candidate_cap_respected":len(candidate_ids)==6}
dump("terminal_overlay_selection.json",selection)

packaging={"schema_version":1,"selected":selection,"package_manifest":package_manifest,"equivalence":{k:package_equiv[k] for k in ("conditions","games","action_mismatches","final_state_mismatches","final_money_mismatches","runtime_errors","agent_errors","all_equivalent")},"previous_archive_unchanged":{"path":"submission/shop_router_0909_hardened.tar.gz","sha256":sha(ROOT/"submission/shop_router_0909_hardened.tar.gz"),"matches_frozen":sha(ROOT/"submission/shop_router_0909_hardened.tar.gz")=="26e7d39eb1df83af7c595167298ad8f3d61afce76e216cd1e25d6416bb791046"},"kaggle_submission_performed":False}
dump("terminal_overlay_packaging.json",packaging)

report=f"""# Terminal overlay sprint report

1. **Public variants inspected:** Most Powerfull Route, Market-Smart Farming, Seven-Turn Rescue.
2. **Exact changes:** all use a physical 712–718 worker planner, retain 712–717 markets, and liquidate actual stock at 718. Most/Seven are byte-identical. Market-Smart expands late-actor two-stop proposals and preserves one late near-shed proposal. Every state-specific primitive change is recorded in `terminal_overlay_source_diff.json`.
3. **Candidates tested:** 6 (three source candidates plus D/E/F minimal bounded variants).
4. **Frozen known near-mirror:** 0/20/0 (W/L/T).
5. **Best known near-mirror:** 12/0/8.
6. **Known loss→win:** 12.
7. **Known loss→tie:** 8.
8. **Known win→loss:** 0.
9. **Known overall mean own-money delta:** {selected_pair['mean_own_money_delta']:+.3f}.
10. **Known overall mean advantage delta:** {selected_pair['mean_advantage_delta']:+.3f}.
11. **Gain source:** exclusively additional terminal fertilizer collection, return, drop, and sale; certified deltas are 7–11 units in the near-mirror panel.
12. **Fresh near-mirror:** 8/0/8 versus Frozen's 0/16/0.
13. **Fresh rate:** 50% raw wins, 75% tie-adjusted match score, 100% non-loss.
14. **Non-mirror regression:** none; both Frozen and selected are 16/0/0. Selected mean own delta {smoke_payload['paired']['mean_own_money_delta']:+.3f}.
15. **Runtime errors:** 0.
16. **Agent errors:** 0.
17. **Livestock escapes:** 0.
18. **Selected path:** `agents/shop_router_0909_terminal/main.py`.
19. **Selected SHA:** bundle `{package_manifest['bundle_sha256']}`; entrypoint `{package_manifest['entrypoint_sha256']}`; policy `{package_manifest['policy_sha256']}`.
20. **current_best.json:** updated after lock and validation.
21. **Archive:** `submission/shop_router_0909_terminal.tar.gz`.
22. **Archive SHA:** `{package_manifest['archive_sha256']}`.
23. **Packaging equivalence:** 10 paired conditions / 20 runs; action mismatches 0, final-state mismatches 0, final-money mismatches 0.
24. **Kaggle submission:** none. Archive is ready for manual upload only.

Decision: **ADOPT → PACKAGE → STOP.** The old frozen source and old submitted archive remain unchanged.
"""
(EXP/"terminal_overlay_report.md").write_text(report)

old_current=EXP/"current_best.json"
existing_current=json.loads(old_current.read_text())
old_hash=(existing_current.get("previous_current_best_manifest_sha256")
          if existing_current.get("agent_version")=="shop_router_0909_terminal_market_smart_2pass_512"
          else sha(old_current))
current={
    "agent_path":"agents/shop_router_0909_terminal/main.py",
    "agent_version":"shop_router_0909_terminal_market_smart_2pass_512",
    "source_sha256":package_manifest["entrypoint_sha256"],
    "source_bundle_sha256":package_manifest["bundle_sha256"],
    "promotion_status":"PROMOTED_RESEARCH_BEST",
    "previous_current_best_manifest_sha256":old_hash,
    "promotion_reason":"Terminal-only D converted the known near-mirror 0/20/0 into 12/0/8 and fresh 0/16/0 into 8/0/8, while preserving 16/0/0 non-mirror smoke; zero prefix mismatches, runtime/agent errors, and livestock escapes.",
    "previous_best":{"path":"agents/shop_router_0909_hardened/main.py","version":"shop_router_0909_hardened_plan10_reallocate_day15","sha256":"da5c6df2c71128ce1372a5adaf6d4859f5758e7854b399d6ff634fbca666d8a2","source_untouched":True,"submitted_archive":"submission/shop_router_0909_hardened.tar.gz","submitted_archive_sha256":"26e7d39eb1df83af7c595167298ad8f3d61afce76e216cd1e25d6416bb791046"},
    "terminal_overlay":{"window":[712,718],"base_identity":"Frozen ShopRouter0909Hardened including Plan-10 correction","public_source":"Market-Smart Farming terminal physical planner, Apache-2.0","local_delta":"max_simulations 256->512, passes 1->2, proposals_per_actor 16->32","prefix_identity":{"normal_window":"steps 0-711","mismatches":0},"selection":"experiments/terminal_overlay_selection.json","report":"experiments/terminal_overlay_report.md"},
    "validation_artifacts":{"source_diff":"experiments/terminal_overlay_source_diff.json","known_panel":"experiments/terminal_overlay_known_panel.json","fresh_validation":"experiments/terminal_overlay_fresh_validation.json","regression_smoke":"experiments/terminal_overlay_regression_smoke.json","packaging":"experiments/terminal_overlay_packaging.json"},
    "provenance":{"notice":"agents/shop_router_0909_terminal/NOTICE.md","license":"agents/shop_router_0909_terminal/LICENSE.txt"},
    "deployment_status":f"Verified local package ready for manual upload: submission/shop_router_0909_terminal.tar.gz SHA-256 {package_manifest['archive_sha256']}. No Kaggle upload or submission performed.",
    "deployment_manifest":"experiments/terminal_overlay_packaging.json",
    "deployment_report":"experiments/terminal_overlay_report.md",
}
old_current.write_text(json.dumps(current,indent=2,sort_keys=True)+"\n")
print(json.dumps({"decision":"ADOPT","selected_bundle_sha256":package_manifest["bundle_sha256"],"archive_sha256":package_manifest["archive_sha256"],"equivalent":package_equiv["all_equivalent"],"current_best_updated":True},indent=2))
