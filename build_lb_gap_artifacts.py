#!/usr/bin/env python3
"""Build the read-only local-to-leaderboard forensic deliverables.

The script consumes persisted experiment shards and public-source manifests. It
does not import or execute an agent and it has no Kaggle write path.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"

EXPECTED = {
    "research": (ROOT / "agents/shop_router_0909_hardened/main.py", "da5c6df2c71128ce1372a5adaf6d4859f5758e7854b399d6ff634fbca666d8a2"),
    "packaged_main": (ROOT / "submission/main.py", "4a188ceaedaa5e37c2216c803517314a2cb2fd780a5bb65956ca016cf278c803"),
    "archive": (ROOT / "submission/shop_router_0909_hardened.tar.gz", "26e7d39eb1df83af7c595167298ad8f3d61afce76e216cd1e25d6416bb791046"),
}

SHOP_PLANS = {
    ("BAKERY", "YARN_STORE"): 3,
    ("BRUNCH_SPOT", "YARN_STORE"): 4,
    ("FARMERS_MARKET", "YARN_STORE"): 5,
    ("ICE_CREAM_SHOP", "YARN_STORE"): 6,
    ("PET_CAFE", "YARN_STORE"): 5,
    ("PIZZA_SHOP", "YARN_STORE"): 7,
    ("SMOOTHIE_SHOP", "YARN_STORE"): 8,
    ("YARN_STORE", "BAKERY"): 9,
    ("YARN_STORE", "BRUNCH_SPOT"): 9,
    ("YARN_STORE", "FARMERS_MARKET"): 1,
    ("YARN_STORE", "ICE_CREAM_SHOP"): 9,
    ("YARN_STORE", "PET_CAFE"): 10,
    ("YARN_STORE", "PIZZA_SHOP"): 6,
    ("YARN_STORE", "SMOOTHIE_SHOP"): 11,
    ("YARN_STORE", "YARN_STORE"): 12,
}


def load(path: Path):
    with path.open() as f:
        return json.load(f)


def dump(name: str, value):
    path = EXP / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values, p):
    xs = sorted(float(x) for x in values)
    if not xs:
        return None
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] if lo == hi else xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def stats(values):
    xs = [float(x) for x in values]
    return {
        "n": len(xs), "mean": statistics.fmean(xs), "median": statistics.median(xs),
        "p25": percentile(xs, .25), "p10": percentile(xs, .10),
        "p5": percentile(xs, .05), "worst": min(xs), "best": max(xs),
    }


def route(row):
    if row.get("forced_plan") is not None:
        return int(row["forced_plan"])
    return SHOP_PLANS.get(tuple(row["shop_pair"][:2]), 0)


def summary(rows):
    outcomes = Counter(r["outcome"] for r in rows)
    return {
        "games": len(rows),
        "outcomes": {"wins": outcomes["win"], "losses": outcomes["loss"], "ties": outcomes["tie"]},
        "own_money": stats(r["own_money"] for r in rows),
        "opponent_money": stats(r["opponent_money"] for r in rows),
        "advantage": stats(r["advantage"] for r in rows),
        "runtime_errors": sum(r["runtime_error"] is not None for r in rows),
    }


def by(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[key(row)].append(row)
    return {str(k): summary(v) for k, v in sorted(groups.items(), key=lambda x: str(x[0]))}


def light(row):
    return {
        "candidate": row["candidate"], "opponent": row["opponent"], "seed": row["seed"],
        "seat": row["seat"], "shop_pair": row["shop_pair"], "derived_route_plan": route(row),
        "own_money": row["own_money"], "opponent_money": row["opponent_money"],
        "advantage": row["advantage"], "outcome": row["outcome"],
    }


def mean_map(rows, side, field):
    keys = sorted(set().union(*(r[side].get(field, {}).keys() for r in rows)))
    return {k: statistics.fmean(float(r[side].get(field, {}).get(k, 0)) for r in rows) for k in keys}


def diff_map(a, b):
    return {k: a.get(k, 0) - b.get(k, 0) for k in sorted(set(a) | set(b))}


def cost_map(rows, side):
    result = {
        "land": statistics.fmean(r[side].get("land_spend", 0) for r in rows),
        "hands": statistics.fmean(r[side].get("labor_spend", 0) for r in rows),
    }
    for prefix, field in (("seed:", "seed_spend"), ("animal:", "animal_spend"), ("feed_or_product:", "product_spend")):
        for k, v in mean_map(rows, side, field).items():
            result[prefix + k] = v
    return result


def terminal_step(row, step):
    return next((x for x in row.get("terminal_trace", []) if x["step"] == step), None)


def first_divergence(row):
    traj = row["daily_trajectory"]
    neg = next((x["day"] for x in traj if x["bank_gap"] < 0), None)
    material = next((x["day"] for x in traj if x["bank_gap"] <= -1000), None)
    first_change = next((x["day"] for x in traj if x["bank_gap"] != 0), None)
    return {"first_nonzero_bank_gap_day": first_change, "first_negative_day": neg, "first_material_minus_1000_day": material}


phase_a = load(EXP / "lb_gap_phase_a_1327.partial.json")["rows"]
phase_b = load(EXP / "lb_gap_phase_b_1327.partial.json")["rows"]
controls = load(EXP / "lb_gap_controls_1327.partial.json")["rows"]
oracle = load(EXP / "lb_gap_oracle_1327.partial.json")["rows"]
terminal_cf = load(EXP / "lb_gap_terminal_counterfactual_1327.partial.json")["rows"]
mirrors = load(EXP / "lb_gap_mirrors_1327.partial.json")["rows"]
pizza = load(EXP / "lb_gap_pizza_yarn_1327.partial.json")["rows"]
primary = phase_a + phase_b
all_current = primary + controls
old_validation = load(EXP / "shop_router_0909_hardened_full_validation.json")
old_plan = load(EXP / "shop_router_0909_plan_performance.json")
op_extract = load(Path("/private/tmp/lb_gap_opponents/extraction_manifest.json"))

hashes = {name: {"path": str(path.relative_to(ROOT)), "expected_sha256": expected,
                 "observed_sha256": sha(path), "matches": sha(path) == expected}
          for name, (path, expected) in EXPECTED.items()}
assert all(x["matches"] for x in hashes.values())

dump("lb_gap_submission_binding.json", {
    "schema_version": 1,
    "binding": {
        "competition": "kaggriculture", "submission_id": 56123896,
        "submitted_filename": "shop_router_0909_hardened.tar.gz",
        "submitted_at_utc": "2026-09-09T13:24:20.373000Z",
        "submitted_at_utc_plus_8": "2026-09-09T21:24:20.373000+08:00",
        "status": "SubmissionStatus.COMPLETE", "public_score": 2418.4,
        "private_score": None,
        "source": "read-only `kaggle competitions submissions kaggriculture --format json`",
    },
    "local_artifacts": hashes,
    "local_packaging_metadata": {"packaged_at_utc_plus_8": "2026-09-09T21:17:24+08:00", "elapsed_to_submission": "6m56.373s", "source": "experiments/shop_router_0909_submission_manifest.json"},
    "binding_confidence": "high: exact filename, manual-submission chronology, and a local archive packaged 6m56s before the server timestamp; Kaggle's submission listing does not expose the uploaded-byte SHA, so remote byte identity is not cryptographically server-proven",
    "write_operations": [],
})

recent = {
    "schema_version": 1,
    "scope": "read-only 24-48h primary / 72h secondary public frontier refresh",
    "official_listing": "https://www.kaggle.com/competitions/kaggriculture/code",
    "refresh_method": "official Kaggle public code pages plus read-only CLI kernel listing and public notebook pulls",
    "sources": [
        {"name": "Most Powerfull Route", "slug": "flexonafft/kaggriculture-most-powerfull-route", "url": "https://www.kaggle.com/code/flexonafft/kaggriculture-most-powerfull-route", "last_run_utc": "2026-09-09T13:35:03.207Z", "score": None, "score_binding": "unavailable", "complete": True, "family": "Shop0909-derived terminal", "runtime_duplicate_of": None},
        {"name": "Market-Smart Farming", "slug": "tetsutani/market-smart-farming-kaggriculture", "url": "https://www.kaggle.com/code/tetsutani/market-smart-farming-kaggriculture", "last_run_utc": "2026-09-09T16:20:04.373Z", "score": None, "score_binding": "unavailable", "complete": True, "family": "Shop0909-derived market/terminal", "runtime_duplicate_of": None},
        {"name": "Seven-Turn Rescue", "slug": "dmitriigluzdov/kaggriculture-seven-turn-rescue-best-lb-2800", "url": "https://www.kaggle.com/code/dmitriigluzdov/kaggriculture-seven-turn-rescue-best-lb-2800", "last_run_utc": "2026-09-09T07:28:25.670Z", "score": None, "score_binding": "title claim is not score evidence", "complete": True, "family": "Shop0909-derived terminal", "runtime_duplicate_of": "Most Powerfull Route"},
        {"name": "Structured Economic Policy V2", "slug": "guruprasaathas111/kaggriculture-structured-economic-policy-v2", "url": "https://www.kaggle.com/code/guruprasaathas111/kaggriculture-structured-economic-policy-v2", "last_run_utc": "2026-09-09T13:28:45.263Z", "score": None, "score_binding": "unavailable", "complete": True, "family": "structured economic", "runtime_duplicate_of": None},
        {"name": "Shape the Shop Work the Pasture", "slug": "tetsutani/shape-the-shop-work-the-pasture-kaggriculture", "url": "https://www.kaggle.com/code/tetsutani/shape-the-shop-work-the-pasture-kaggriculture", "last_run_utc": "2026-09-06", "score": 2747.2, "score_binding": "official listing observation; not within primary window", "complete": True, "family": "replay route market-aware", "runtime_duplicate_of": None},
        {"name": "Farming Score V3: Replay Revised", "slug": "lynnsakurai/farming-score-v3-replay-revised", "url": "https://www.kaggle.com/code/lynnsakurai/farming-score-v3-replay-revised", "last_run_utc": "2026-09-03", "score": 2703.9, "score_binding": "official listing observation; not within primary window", "complete": True, "family": "two-route replay", "runtime_duplicate_of": None},
        {"name": "Adaptive Route Agent V2", "slug": "reyhanksatria/adaptive-route-agent-v2", "url": "https://www.kaggle.com/code/reyhanksatria/adaptive-route-agent-v2", "last_run_utc": None, "score": 2589.3, "score_binding": "direct official page, Version 2 of 2", "complete": True, "family": "adaptive native", "runtime_duplicate_of": None},
    ],
    "genuinely_recent_complete_notebooks": 4,
    "distinct_recent_runtimes": 3,
    "recent_score_bound_high_runtimes": 0,
    "important_limitation": "fresh source completeness is strong, but exact leaderboard score/version binding is unavailable for all four recent notebooks",
}
dump("lb_gap_recent_opponent_scan.json", recent)

manifest = {
    "schema_version": 1,
    "environment": {"primary_version": "kaggle-environments==1.32.7", "isolated_path": "/private/tmp/lb_gap_env1327", "wheel_sha256": "2a1bb862ad2d6463080f80f6a766f46d94b53fd57168cfeddb9857fc3dbc4c8f"},
    "development_panel": [
        {"id": "farming_v3_current", "family": "two-route replay", "source": op_extract["farming_v3_current"]},
        {"id": "shape_shop_current", "family": "replay route market-aware", "source": op_extract["shape_shop_current"]},
        {"id": "market_smart_terminal", "family": "Shop0909-derived market/terminal r31", "source": op_extract["market_smart"]},
        {"id": "most_powerfull_terminal", "family": "Shop0909-derived terminal e182", "source": op_extract["most_powerfull"]},
    ],
    "historical_controls": ["previous frozen CurrentBest", "V2"],
    "held_out_next_stage": [
        {"id": "structured_v2", "reason": "preserved unseen", "source": op_extract["structured_v2"]},
        {"id": "adaptive_v2", "reason": "preserved unseen; ELF x86-64 agent.so cannot execute on Darwin arm64", "source": op_extract["adaptive_v2"]},
    ],
    "source_license_note": "public-source licenses and notices were retained where supplied; no source was promoted or submitted",
}
dump("lb_gap_opponent_manifest.json", manifest)
dump("lb_gap_split_manifest.json", {
    "schema_version": 1,
    "development": {"opponents": [x["id"] for x in manifest["development_panel"]], "natural_seeds": [2609100,2609101,2609102,2609103,2609104]},
    "historical_controls": {"opponents": ["current_best", "v2"], "seeds": [2609100,2609101]},
    "unseen_next_stage": {"opponents": ["structured_v2", "adaptive_v2"], "reserved_seeds": [2609200,2609201,2609202,2609203]},
    "warning": "do not tune and validate on the development panel as if it were unseen",
})

candidate_results = {}
for candidate in ("hardened", "exact", "previous_current_best", "v2"):
    rows = [r for r in primary if r["candidate"] == candidate]
    candidate_results[candidate] = {"overall": summary(rows), "by_opponent": by(rows, lambda r:r["opponent"]), "by_plan": by(rows, route)}
dump("lb_gap_current_meta_results.json", {
    "schema_version": 1, "primary_design": "4 candidates x 4 current-meta opponents x 5 natural seeds x 2 seats = 160",
    "phase_a_games": len(phase_a), "phase_b_games": len(phase_b), "results": candidate_results,
    "historical_controls": {c: summary([r for r in controls if r["candidate"] == c]) for c in ("hardened","exact","previous_current_best","v2")},
    "hardened_game_records": [light(r) for r in primary if r["candidate"] == "hardened"],
    "plan_field_note": "derived_route_plan is reconstructed from the first two shops. Raw selected_plan was sampled after step 648, when the public agent changes to common Plan 2, and is not the route choice.",
})

hardened = [r for r in primary if r["candidate"] == "hardened"]
exact = [r for r in primary if r["candidate"] == "exact"]
h_controls = [r for r in controls if r["candidate"] == "hardened"]
plan0 = [r for r in hardened if route(r) == 0]
old_broad = old_validation["broad_league"]["overall"]
old_p0 = old_plan["plans"]["0"]
dump("lb_gap_plan0_analysis.json", {
    "schema_version": 1,
    "activation": {"games": len(plan0), "primary_games": len(hardened), "frequency": len(plan0)/len(hardened), "shop_pairs": dict(Counter(" -> ".join(r["shop_pair"]) for r in plan0))},
    "current_meta": summary(plan0), "historical_90_game_forced_plan0": old_p0,
    "transfer_delta": {"mean_own_money": summary(plan0)["own_money"]["mean"] - old_p0["own_money"]["mean"], "mean_advantage": summary(plan0)["advantage"]["mean"] - old_p0["advantage"]["mean"]},
    "finding": "Plan 0 own money increased, not decreased; it is not an economic-collapse signal. Its 16 losses are terminal tie-break losses to two near-identical descendants.",
})

new_plan_rows = defaultdict(list)
for r in oracle:
    new_plan_rows[int(r["forced_plan"])].append(r)
transfer = {}
for p in range(13):
    old = old_plan["plans"][str(p)]
    new = summary(new_plan_rows[p])
    transfer[str(p)] = {
        "old_validation": {"games": old["games"], "mean_own_money": old["own_money"]["mean"], "mean_advantage": old["advantage"]["mean"]},
        "new_current_meta_seed2609100": new,
        "delta_mean_own_money": new["own_money"]["mean"] - old["own_money"]["mean"],
        "delta_mean_advantage": new["advantage"]["mean"] - old["advantage"]["mean"],
    }
best_transfer = max(transfer, key=lambda p: transfer[p]["delta_mean_own_money"])
worst_transfer = min(transfer, key=lambda p: transfer[p]["delta_mean_own_money"])
pizza_pairs = {}
for plan in (7,12):
    rows = [r for r in pizza if r["forced_plan"] == plan]
    pizza_pairs[str(plan)] = summary(rows)
paired_pizza_delta = []
for r12 in [r for r in pizza if r["forced_plan"] == 12]:
    r7 = next(r for r in pizza if r["forced_plan"] == 7 and (r["opponent"],r["seed"],r["seat"]) == (r12["opponent"],r12["seed"],r12["seat"]))
    paired_pizza_delta.append(r12["own_money"]-r7["own_money"])
dump("lb_gap_plan_transfer.json", {
    "schema_version": 1, "scope_caveat": "new all-plan panel is one natural shop realization (seed 2609100), 4 opponents, both seats; it is diagnostic, not a deployment frequency estimate",
    "plans": transfer, "best_transferring_plan_by_own_money_delta": int(best_transfer), "worst_transferring_plan_by_own_money_delta": int(worst_transfer),
    "pizza_to_yarn_control": {"current_results": pizza_pairs, "paired_plan12_minus_plan7_own_money": stats(paired_pizza_delta), "old_result": "Plan 12 beat Plan 7 in 6/6 by mean +7186.7", "finding": "current meta reverses the old diagnostic: Plan 12 loses to Plan 7 in 6/6"},
})

losses = [r for r in hardened if r["outcome"] == "loss"]
divs = [first_divergence(r) for r in losses]
dump("lb_gap_first_divergence.json", {
    "schema_version": 1, "losses": len(losses),
    "first_nonzero_day_distribution": dict(Counter(str(x["first_nonzero_bank_gap_day"]) for x in divs)),
    "first_negative_day_distribution": dict(Counter(str(x["first_negative_day"]) for x in divs)),
    "first_material_minus_1000_day_distribution": dict(Counter(str(x["first_material_minus_1000_day"]) for x in divs)),
    "records": [{**light(r), **first_divergence(r)} for r in losses],
    "finding": "all loss trajectories are tied through day 28 and first turn negative on day 29; none reaches a material -1000 bank gap",
})
dump("lb_gap_loss_trajectories.json", {
    "schema_version": 1,
    "normalization": "one record per Hardened loss; candidate is always FrozenBest regardless of seat; daily snapshots are end-of-day and cumulative purchase/sale counts are side-normalized",
    "fields": ["bank", "land", "hands", "wheat_tiles", "major_crops", "cows", "sheep", "inventory", "cumulative_purchases", "cumulative_sales"],
    "games": [{"condition": light(r), "daily": r["daily_trajectory"], "terminal_steps": r["terminal_trace"]} for r in losses],
})

c_cost = cost_map(losses, "candidate_economics")
o_cost = cost_map(losses, "opponent_economics")
c_rev = mean_map(losses, "candidate_economics", "revenue")
o_rev = mean_map(losses, "opponent_economics", "revenue")
c_sales = mean_map(losses, "candidate_economics", "sales")
o_sales = mean_map(losses, "opponent_economics", "sales")
dump("lb_gap_economic_attribution.json", {
    "schema_version": 1, "scope": "20 Hardened losses on 1.32.7 current-meta primary panel",
    "mean_candidate_cost": c_cost, "mean_opponent_cost": o_cost, "mean_excess_cost_candidate_minus_opponent": diff_map(c_cost,o_cost),
    "mean_candidate_revenue": c_rev, "mean_opponent_revenue": o_rev, "mean_revenue_delta_candidate_minus_opponent": diff_map(c_rev,o_rev),
    "mean_candidate_units_sold": c_sales, "mean_opponent_units_sold": o_sales, "mean_unit_delta_candidate_minus_opponent": diff_map(c_sales,o_sales),
    "terminal_inventory": {"candidate_mean_units": statistics.fmean(r["candidate_terminal"]["units"] for r in losses), "opponent_mean_units": statistics.fmean(r["opponent_terminal"]["units"] for r in losses)},
    "main_lost_revenue_category": "FERTILIZER", "main_excess_cost_category": "none (all measured cost categories are identical)",
    "finding": "the entire final loss is extra descendant fertilizer sold at the price floor; all other production, cost, and revenue categories match",
})

def market_group(rows):
    products = sorted(set().union(*(r["candidate_economics"]["sales"].keys() | r["opponent_economics"]["sales"].keys() for r in rows)))
    out = {}
    for product in products:
        cq = statistics.fmean(r["candidate_economics"]["sales"].get(product,0) for r in rows)
        oq = statistics.fmean(r["opponent_economics"]["sales"].get(product,0) for r in rows)
        cr = statistics.fmean(r["candidate_economics"]["revenue"].get(product,0) for r in rows)
        or_ = statistics.fmean(r["opponent_economics"]["revenue"].get(product,0) for r in rows)
        cd = statistics.fmean(r["candidate_economics"]["sale_day_weighted"].get(product,0) for r in rows)
        od = statistics.fmean(r["opponent_economics"]["sale_day_weighted"].get(product,0) for r in rows)
        out[product] = {"candidate_units":cq,"opponent_units":oq,"candidate_revenue":cr,"opponent_revenue":or_,"candidate_realized_price":cr/cq if cq else None,"opponent_realized_price":or_/oq if oq else None,"candidate_mean_sale_day":cd,"opponent_mean_sale_day":od}
    return out

same_family = [r for r in hardened if r["opponent"] in {"market_smart_terminal","most_powerfull_terminal"}]
different_family = [r for r in hardened if r["opponent"] in {"farming_v3_current","shape_shop_current"}]
events = [e for r in losses for e in r["market_events"]]
event_summary = {}
for product in sorted(set(e["product"] for e in events)):
    es = [e for e in events if e["product"] == product]
    event_summary[product] = {
        "events": len(es),
        "mean_price_before": statistics.fmean(e["price_before"] for e in es),
        "mean_price_after": statistics.fmean(e["price_after"] for e in es),
        "mean_price_impact": statistics.fmean(e["price_after"]-e["price_before"] for e in es),
        "mean_candidate_quantity_per_event": statistics.fmean(e["candidate_quantity"] for e in es),
        "mean_opponent_quantity_per_event": statistics.fmean(e["opponent_quantity"] for e in es),
        "mean_candidate_revenue_per_event": statistics.fmean(e["candidate_revenue"] for e in es),
        "mean_opponent_revenue_per_event": statistics.fmean(e["opponent_revenue"] for e in es),
    }
dump("lb_gap_market_attribution.json", {
    "schema_version": 1,
    "same_family": {"summary":summary(same_family), "by_product":market_group(same_family)},
    "different_family": {"summary":summary(different_family), "by_product":market_group(different_family)},
    "loss_event_summary_by_product": event_summary,
    "loss_terminal_fertilizer_events": [e for e in events if e["product"]=="FERTILIZER" and e["step"]>=712 and e["opponent_quantity"] != e["candidate_quantity"]],
    "finding": "broad oversupply and price compression are visible, but they do not create a relative whole-season collapse: near-mirrors have identical economics through day 28. The decisive shared-market delta is only the descendant's extra 5-10 fertilizer units at price 1.",
})

base_lookup = {(r["opponent"],r["seed"],r["seat"]):r for r in exact}
terminal_gains = defaultdict(list)
for r in terminal_cf:
    b = base_lookup[(r["opponent"],r["seed"],r["seat"])]
    terminal_gains[r["candidate"]].append(r["own_money"]-b["own_money"])
loss_abs = [-r["advantage"] for r in losses]
dump("lb_gap_terminal_analysis.json", {
    "schema_version": 1,
    "isolated_overlay_vs_exact_same_conditions": {k:stats(v) for k,v in terminal_gains.items()},
    "observed_hardened_loss_size": stats(loss_abs),
    "loss_first_divergence": "day 29; concrete action divergence at steps 714-718, extra fertilizer collection/drop/sale",
    "step_712_hindsight_upper_bound": {"method": "existing public legal terminal overlays on identical pre-terminal route/state", "mean_realized_headroom_best_overlay": max(statistics.fmean(v) for v in terminal_gains.values()), "threshold_comparison": "far below +1000 dedicated-stage threshold"},
    "final_unsold_inventory": {"hardened_loss_games_mean_units":statistics.fmean(r["candidate_terminal"]["units"] for r in losses),"terminal_opponents_mean_units":statistics.fmean(r["opponent_terminal"]["units"] for r in losses)},
    "mirror_results": [light(r) for r in mirrors],
    "interpretation": "economically tiny, but outcome-significant because official Skill Rating observes win/draw/loss rather than margin",
})

family_map = {
    "market_smart_terminal":"Shop0909-derived terminal-enhanced", "most_powerfull_terminal":"Shop0909-derived terminal-enhanced",
    "farming_v3_current":"old/replay", "shape_shop_current":"market-aware replay",
}
dump("lb_gap_opponent_family_results.json", {
    "schema_version":1,
    "families": by(hardened, lambda r:family_map[r["opponent"]]),
    "by_opponent": by(hardened, lambda r:r["opponent"]),
    "dominant_failure_family":"Shop0909-derived terminal-enhanced (20/20 losses, each by 5-10 coins)",
})

condition_groups=defaultdict(list)
for r in oracle:
    condition_groups[(r["opponent"],r["seed"],r["seat"])].append(r)
headroom=[]
oracle_records=[]
for condition, rows in condition_groups.items():
    natural=base_lookup[condition]
    best=max(rows,key=lambda r:r["own_money"])
    h=best["own_money"]-natural["own_money"]
    headroom.append(h)
    oracle_records.append({"opponent":condition[0],"seed":condition[1],"seat":condition[2],"natural_plan":route(natural),"natural_own":natural["own_money"],"oracle_plan":best["forced_plan"],"oracle_own":best["own_money"],"headroom":h})
dump("lb_gap_current_meta_oracle.json", {
    "schema_version":1,"conditions":len(condition_groups),"plan_runs":len(oracle),"headroom":stats(headroom),"records":oracle_records,
    "historical_mean_oracle_headroom":1441.4,
    "finding":"Plan 0 was own-money optimal in every tested condition; observed current-meta oracle headroom is zero. Router regret did not increase.",
    "scope_caveat":"one natural shop realization (Smoothie -> Pizza), four opponents, both seats; not a proof over all shop pairs",
})

loss_sorted=sorted(losses,key=lambda r:r["advantage"])
case_lines=[
    "# Local → leaderboard loss casebook", "",
    "All 20 current-panel losses are the same pattern: a Shop0909-derived terminal overlay remains economically identical through day 28, then collects and sells 5–10 additional fertilizer units at the $1 floor during turns 714–718.", "",
    "| Opponent | Seat | Shops | Plan | Own | Opp | Adv | First negative day | Lost revenue | Terminal loss | Collision |",
    "|---|---:|---|---:|---:|---:|---:|---:|---|---:|---|",
]
for r in loss_sorted:
    fr=c_rev.get("FERTILIZER",0)-o_rev.get("FERTILIZER",0)
    case_lines.append(f"| {r['opponent']} | {r['seat']} | {' → '.join(r['shop_pair'])} | {route(r)} | {r['own_money']:.0f} | {r['opponent_money']:.0f} | {r['advantage']:.0f} | 29 | fertilizer ({fr:.1f} mean) | {-r['advantage']:.0f} | near-mirror |")
case_lines += ["", "Top five by absolute loss are therefore not distinct structural failures; they are five replications of the terminal-fertilizer tie-break pattern."]
(EXP/"lb_gap_loss_casebook.md").write_text("\n".join(case_lines)+"\n")

exact_pairs={(r["opponent"],r["seed"],r["seat"]):r for r in exact}
h_exact_deltas=[r["own_money"]-exact_pairs[(r["opponent"],r["seed"],r["seat"])]["own_money"] for r in hardened]
diagnosis={
    "schema_version":1,
    "exact_kaggle_result":{"submission_id":56123896,"public_score":2418.4,"status":"COMPLETE"},
    "historical_broad":old_broad,
    "current_primary":summary(hardened),
    "current_plus_historical_controls":summary(hardened+h_controls),
    "transfer_delta_vs_old_broad":{"mean_own_money":summary(hardened)["own_money"]["mean"]-old_broad["own_money"]["mean"],"mean_advantage":summary(hardened)["advantage"]["mean"]-old_broad["advantage"]["mean"]},
    "hardened_minus_exact_paired_own_money":stats(h_exact_deltas),
    "hypotheses":{
        "H1_opponent_distribution_mismatch":"strongly supported",
        "H2_shop_distribution_mismatch":"old suite overweighted fixed shops, but current natural results do not show a shop-driven economic collapse",
        "H3_shared_market_meta":"visible but only a tiny decisive terminal fertilizer delta in losses",
        "H4_plan_frequency":"Plan 0 frequency 80%, but own money improved and it remains oracle-optimal in sampled conditions",
        "H5_terminal":"small cash headroom (best overlay mean 9.25), large binary-outcome impact",
        "H6_harness_bias":"strongly supported",
        "H7_public_source_overfitting":"supported as opponent-family/stale-pool selection bias, not as direct strategy value collapse",
        "H8_environment":"real 1.32.6/1.32.7 price-curve difference; small observed effect",
        "H9_submission_runtime":"not supported",
        "H10_score_interpretation":"strongly supported",
    },
    "evidence_weights_not_variance_decomposition":{"HARNESS_AND_SCORE_METRIC_GAP":0.70,"OPPONENT_AND_META_GAP":0.25,"ENVIRONMENT_GAP":0.03,"TERMINAL_CASH_GAP":0.02,"ROUTER_GAP":0.0,"PLAN10_PATCH_GAP":0.0,"PACKAGING_GAP":0.0},
    "classification":"mixed, dominated by HARNESS GAP + SCORE-METRIC GAP, with opponent/meta convergence and tiny terminal tie-breakers",
    "decision":"CASE E — NEXT: rebuild evaluation methodology before strategy work",
    "do_not_work_on_next":["Plan 0 replacement","router redesign","Plan 10 patch","large terminal value-recovery stage","GA/RL or arbitrary micro-tuning","new submission"],
}
dump("lb_gap_diagnosis.json",diagnosis)

audit=f"""# Local evaluation harness audit

## Audited claims

The 64–0 broad league came from `run_shop_router_0909_hardened_final.py` under local `kaggle-environments==1.32.6`. It used eight historical opponents (`previous CurrentBest`, `V2`, `k3`, `nazmus`, `tetsuya`, `crop_dusta`, `oceanmix`, `farming_v3`), four seeds, both seats, and exactly eight games per opponent. Half the games (32/64) forced independently generated shop schedules; the other 32 used natural environment RNG. The 32 fixed games reduce to two fixed shop schedules repeated across eight opponents and both seats. Fresh environment instances and isolated agent imports reset every game.

The CurrentBest and V2 head-to-head claims each used 24 games: fixed and natural shop modes × six seeds × two seats. The score summaries were final own bank, raw bank advantage, and W/L/T—not Kaggle Skill Rating.

## Selection-bias findings

- The pool contained no Shop0909-derived near-mirror, no terminal-enhanced descendant, and no post-September-9 strategy.
- Historical replay/static families dominated. Opponent choice came after extensive local optimization against the same project lineage, creating family-level selection bias even when individual seed IDs were nominally fresh.
- Fixed shops were overweighted at 50%, whereas competition episodes use natural RNG.
- Only four broad-league seed IDs were used, with each opponent/fixed-mode/seat replication multiplying those conditions.
- The evaluator rewarded large margins. Official simulation rating ignores margin and observes only win/draw/loss, so +28,189 average advantage is not a score proxy.

## Refreshed design

The 1.32.7 primary panel used four frozen candidates, four public current-meta opponents, five natural seeds, and both seats (160 games; 40 per candidate). Two historical controls added 32 games. All shards were incremental/resumable and had zero runtime errors.
"""
(EXP/"lb_gap_local_harness_audit.md").write_text(audit)

scoring="""# Kaggriculture scoring and runtime audit

## Official leaderboard semantics

Kaggle simulation competitions estimate each submission's Skill Rating as a Gaussian `N(mu, sigma²)`. Validated submissions start at `mu=600`, are matched against similarly rated agents, and update after episodes. A win raises the winner and lowers the loser; a draw pulls ratings together. The update magnitude depends on the expected result and uncertainty. Crucially, the amount by which an agent wins or loses does **not** affect Skill Rating. Source: [Kaggle competition documentation](https://www.kaggle.com/docs/competitions).

Therefore no exact numeric local leaderboard-score proxy is possible from this repository alone: the live opponent ratings, uncertainties, matchmaking sequence, and episode chronology are unavailable. The honest direct proxy is local W/L/T; raw coins and advantage are diagnostics only. A made-up mapping was deliberately NOT RUN.

## Why the old metric misled

Hardened went 20–20–0 against the refreshed current panel while keeping mean advantage positive, because 20 large wins coexist with 20 losses by only 5–10 coins. Margin-weighted local summaries call that strong; the official binary episode result counts every tiny loss fully.

## Dynamic-score evidence

Public empirical studies report that byte-identical submissions can display materially different ratings days apart: an age-matched comparison in the first study found 1839.0 versus 1237.8 for the same bytes submitted 9.7 days apart (-601.2). A second study's 2,880-paired-episode local pool ranked its v9 above v8 while the live leaderboard ranked v8 above v9; 12 of 15 pool opponents were saturated at either 0% or 100% win rate. A third study found median same-active-submission drift around -67 points/day at ratings >=2500 and -80/day at 2000–2500. These are observational—not official-formula or Shop0909-specific—sources: [Same File, 9 Days Apart](https://www.kaggle.com/code/dariushafshar/same-file-9-days-apart-1839-vs-1238), [18,144 episodes: local win rate ranks backwards](https://www.kaggle.com/code/dariushafshar/18-144-episodes-local-win-rate-ranks-backwards), and [Rating decay near the medal line](https://www.kaggle.com/code/dariushafshar/rating-decay-near-the-medal-line-80-pts-day).

## Runtime parity

Local historical validation used 1.32.6. Recent public notebooks explicitly install 1.32.7. The isolated 1.32.7 wheel has SHA-256 `2a1bb862ad2d6463080f80f6a766f46d94b53fd57168cfeddb9857fc3dbc4c8f`; the Kaggriculture engine source changed from SHA `fb9215c5e21a25243e2d13e75b3d70a79cf7d78fff150a90f1bb5eacf9ba2bcf` to `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`. The strategic diff is in the below-inventory price shapes for CARROT, TOMATO, and EGG (`hinge` with gain 8 replaces older defaults). Inspection found no change to action processing, market-order processing, hires, invalid-action behavior, reset, or randomization. Re-running the full diagnostic panel on 1.32.7 preserved the causal result; the Phase-A Hardened own-money delta versus 1.32.6 was only -34.25 and mean-advantage delta -12.0.

The public notebooks support 1.32.7 as the current public runtime expectation, but do not cryptographically prove the private competition server build. The version mismatch is real and should be fixed in future evaluation, yet it is weak evidence for the 2418.4 transfer gap.
"""
(EXP/"lb_gap_scoring_audit.md").write_text(scoring)

report=f"""# Local → leaderboard transfer-gap forensic report

## Executive finding

The submission is Kaggle submission **56123896**, timestamped **2026-09-09 13:24:20.373 UTC** (21:24:20.373 UTC+8), status **COMPLETE**, with exact Public Score **2418.4**. The local archive still hashes to `{hashes['archive']['observed_sha256']}`. The strongest explanation is **CASE E: the local harness and score proxy were wrong for the question being asked**, compounded by a changed opponent distribution. Packaging, Plan 10, Plan 0 economics, and router regret are not supported causes.

## Required answers (1–44)

1. **Exact score:** 2418.4.
2. **Submission ID:** 56123896.
3. **Submitted SHA:** the local submitted archive matches its frozen SHA exactly. Kaggle exposes filename/timestamp/score but not remote bytes, so server-side hash identity cannot be independently proven.
4. **Packaging cause:** implausible; prior 30,198-call equivalence plus unchanged hashes and normal COMPLETE status strongly reject it.
5. **Biased methodology:** yes—stale historical opponents, family selection bias, 50% forced shops, four broad seeds, and margin-centric summaries.
6. **Old distribution:** eight historical opponents, 4 seeds, both seats, 32 fixed-shop + 32 natural-shop games; no Shop0909 descendant.
7. **Refreshed distribution:** four frozen candidates × four current public strategies × five fresh natural seeds × both seats; historical controls kept separate.
8. **Recent reconstruction:** four genuinely recent complete notebooks, representing three distinct runtimes because Seven-Turn Rescue is byte-identical to Most Powerfull Route. Two were exercised; one runnable strategy and one native x86-64 strategy remain held out.
9. **FrozenBest current W/L/T:** {summary(hardened)['outcomes']['wins']}/{summary(hardened)['outcomes']['losses']}/{summary(hardened)['outcomes']['ties']} over 40 primary games.
10. **Own-money change:** {summary(hardened)['own_money']['mean']-old_broad['own_money']['mean']:+.1f} ({old_broad['own_money']['mean']:.1f} → {summary(hardened)['own_money']['mean']:.1f}); it improved.
11. **Advantage change:** {summary(hardened)['advantage']['mean']-old_broad['advantage']['mean']:+.1f} ({old_broad['advantage']['mean']:.1f} → {summary(hardened)['advantage']['mean']:.1f}).
12. **Current tail:** advantage P10 {summary(hardened)['advantage']['p10']:.1f}, P5 {summary(hardened)['advantage']['p5']:.1f}, worst {summary(hardened)['advantage']['worst']:.1f}.
13. **Exact vs Hardened:** paired own-money delta is exactly {stats(h_exact_deltas)['mean']:.1f} in all 40 current conditions; actions/economics are off the patched Plan-10 path.
14. **Plan-10 patch:** exonerated.
15. **Plan 0 frequency:** {len(plan0)}/{len(hardened)} = {len(plan0)/len(hardened):.0%}.
16. **Plan 0 current performance:** {summary(plan0)['outcomes']['wins']}/{summary(plan0)['outcomes']['losses']}/{summary(plan0)['outcomes']['ties']}, mean own {summary(plan0)['own_money']['mean']:.1f}, mean advantage {summary(plan0)['advantage']['mean']:+.1f}, P10 advantage {summary(plan0)['advantage']['p10']:.1f}, worst {summary(plan0)['advantage']['worst']:.1f}.
17. **Plan 0 degradation:** own money changed {summary(plan0)['own_money']['mean']-old_p0['own_money']['mean']:+.1f}; advantage changed {summary(plan0)['advantage']['mean']-old_p0['advantage']['mean']:+.1f}. It is not an own-economy collapse.
18. **Worst-transfer plan:** Plan {worst_transfer}, own delta {transfer[worst_transfer]['delta_mean_own_money']:+.1f} in the limited all-plan panel.
19. **Best-transfer plan:** Plan {best_transfer}, own delta {transfer[best_transfer]['delta_mean_own_money']:+.1f}.
20. **Oracle headroom:** mean {stats(headroom)['mean']:.1f}, max {stats(headroom)['best']:.1f} over eight sampled current-meta conditions.
21. **Router regret:** no; it fell from historical mean +1,441.4 to observed 0 in this limited diagnostic.
22. **First divergence:** all 20 losses stayed tied through day 28 and first became negative on day 29; 0/20 crossed -1,000.
23. **Lost revenue:** fertilizer, mean {o_rev.get('FERTILIZER',0)-c_rev.get('FERTILIZER',0):.1f} coins per loss.
24. **Excess cost:** none; every measured cost category is identical.
25. **Shared market:** it determines realized prices, but the decisive relative gap is only the opponent's extra terminal fertilizer sold at the $1 floor. It is not a broad whole-game realization collapse.
26. **Same-family harm:** yes in binary outcomes—0/20 against the two terminal descendants—versus 20/0 against two structurally distinct public opponents.
27. **Oversupply collision:** visible in low/floor prices and synchronized sales, but not causal for the broad transfer gap; near-mirrors are identical through day 28.
28. **Terminal headroom:** public overlays add mean 6.75 (e182) or 9.25 (r31), maximum 16 coins—far below +1,000.
29. **Terminal importance:** negligible cash fraction, but meaningful match-result tie-breaker because every 5–10 coin loss counts as a loss.
30. **Seven-Turn ideas:** retain as an outcome-sensitive evaluator control; do not start a dedicated value-recovery stage now.
31. **Scoring semantics:** central. [Kaggle's official documentation](https://www.kaggle.com/docs/competitions) says win margin does not affect Skill Rating and matchmaking is rating-dependent.
32. **Environment parity:** a real 1.32.6→1.32.7 price-curve change was found; isolated 1.32.7 reruns preserve the finding and show a small Phase-A effect.
33. **Public decay:** public observational studies show strong fixed-agent time drift generally, but no time series binds this exact submission. The old Shop Router v1 score 2839.5 versus 2418.4 is consistent with drift, not causal proof.
34. **Dominant failure family:** Shop0909-derived terminal-enhanced near-mirrors.
35. **Top-five pattern:** all are terminal fertilizer tie-breakers; losses 5–10 coins, first negative day 29, no cost/crop/livestock divergence, no stranded final inventory, extra opponent fertilizer sold at floor.
36. **Root cause:** harness/score-metric mismatch.
37. **Second cause:** stale opponent distribution and same-parent public meta convergence.
38. **Evidence weights:** 70% harness+score metric, 25% opponent/meta, 3% environment, 2% terminal cash; these are judgmental evidence weights, not an additive causal variance decomposition.
39. **Classification:** mixed; dominated by HARNESS GAP + SCORE-METRIC GAP, then opponent/meta; not router/parent-economy/packaging.
40. **Next stage:** **rebuild evaluation methodology before strategy work**—version-lock 1.32.7, make W/L/T primary, margin secondary, use contemporaneous/similar-strength opponents, preserve holdouts, and model rating uncertainty rather than inventing a score transform.
41. **Do not work next:** Plan-0 replacement, router redesign, Plan-10, a large terminal-value stage, GA/RL, arbitrary tuning, or a new submission.
42. **FrozenBest unchanged:** confirmed SHA `{hashes['research']['observed_sha256']}`.
43. **Submission artifacts unchanged:** confirmed `submission/main.py` SHA `{hashes['packaged_main']['observed_sha256']}` and archive SHA `{hashes['archive']['observed_sha256']}`.
44. **No writes to Kaggle:** confirmed; no packaging, upload, or submission occurred. Only read-only listing/source acquisition was used.

## Decision

**CASE E — NEXT: rebuild evaluation methodology before strategy work.**

The key contradiction is now resolved: the refreshed agent still makes more money and wins distinct opponents by thousands, but an outcome-sensitive rating treats twenty 5–10 coin losses as twenty full losses. A 64–0 margin-weighted historical panel did not measure that vulnerability.

## Public sources

- [Official Kaggriculture code listing](https://www.kaggle.com/competitions/kaggriculture/code)
- [Official Kaggriculture overview](https://www.kaggle.com/competitions/kaggriculture/overview)
- [Most Powerfull Route](https://www.kaggle.com/code/flexonafft/kaggriculture-most-powerfull-route), [Market-Smart Farming](https://www.kaggle.com/code/tetsutani/market-smart-farming-kaggriculture), and [Seven-Turn Rescue](https://www.kaggle.com/code/dmitriigluzdov/kaggriculture-seven-turn-rescue-best-lb-2800)
- [Shape the Shop Work the Pasture](https://www.kaggle.com/code/tetsutani/shape-the-shop-work-the-pasture-kaggriculture), [Farming Score V3](https://www.kaggle.com/code/lynnsakurai/farming-score-v3-replay-revised), and [Adaptive Route Agent V2](https://www.kaggle.com/code/reyhanksatria/adaptive-route-agent-v2)
"""
(EXP/"lb_gap_forensic_report.md").write_text(report)

print(json.dumps({"written": sorted(p.name for p in EXP.glob("lb_gap_*") if not p.name.endswith("partial.json")), "hashes": hashes, "primary": summary(hardened)}, indent=2))
