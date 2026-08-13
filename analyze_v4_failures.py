"""Build V4 real-failure diagnostics from the frozen deployed V2 corpus.

This deliberately reuses the financially exact V2 analyzer.  It writes only
new V4 artifacts and never mutates the route, source agent, or deployment.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import statistics

import analyze_v2_real_kaggle as base


ROOT = Path(__file__).resolve().parent
DIAGNOSTICS = ROOT / "experiments/v4_real_failure_diagnostics.json"
REPORT = ROOT / "experiments/v4_real_failure_diagnostics.md"
CLUSTERS = ROOT / "experiments/v4_failure_clusters.json"


def percentile(values, fraction):
    values = sorted(float(value) for value in values)
    if not values:
        return None
    point = fraction * (len(values) - 1)
    lower = int(point)
    weight = point - lower
    return values[lower] * (1 - weight) + values[min(lower + 1, len(values) - 1)] * weight


def product_totals(rows, field):
    products = sorted({product for row in rows for product in row["economy"].get(field, {})})
    return {
        product: statistics.fmean(row["economy"].get(field, {}).get(product, 0) for row in rows)
        for product in products
    } if rows else {}


def final_period(row, first_day=20):
    days = [day for day in row["daily"] if int(day.get("day", -1)) >= first_day]
    revenue = Counter()
    sales = Counter()
    spending = Counter()
    for day in days:
        revenue.update(day.get("sale_revenue", {}))
        sales.update(day.get("sales", {}))
        spending.update({
            "seed": sum(day.get("seed_spending", {}).values()),
            "feed": sum(day.get("feed_spending", {}).values()),
            "animal": sum(day.get("animal_spending", {}).values()),
            "labor": day.get("labor_spending", 0),
            "land": day.get("land_spending", 0),
        })
    return {"revenue": dict(revenue), "sales": dict(sales), "spending": dict(spending)}


def classify(row, cohort):
    late = final_period(row)
    total_revenue = float(row["economy"].get("total_sale_revenue", 0))
    cohort_revenue = statistics.median(
        peer["economy"].get("total_sale_revenue", 0) for peer in cohort
    ) if cohort else total_revenue
    last_checkpoint = row["checkpoints"][-1]
    physical_intact = (
        row["economy"].get("max_productive_tiles", 0) >= 70
        and sum(row["economy"].get("peak_animals", {}).values()) >= 12
        and last_checkpoint.get("quadrant_delta", 0) == 0
        and abs(last_checkpoint.get("productive_delta", 0)) <= 8
    )
    tags = []
    if physical_intact and total_revenue < cohort_revenue - 2500:
        tags.append("market_realization")
    if row.get("first_large_divergence_step") is not None and row["first_large_divergence_step"] >= 570:
        tags.append("endgame_timing")
    if last_checkpoint.get("money_delta", 0) < -1500 and physical_intact:
        tags.append("capital_shortfall_after_production")
    if row.get("final_inventory_value", 0) > 500:
        tags.append("endgame_stranding")
    if row.get("route_divergence_count", 0) >= 3:
        tags.append("route_drift")
    if not tags:
        tags.append("opponent_economic_advantage")
    primary = (
        "endgame_inefficiency" if "endgame_timing" in tags and abs(row["margin"]) < 2500
        else "market_realization_deficit" if "market_realization" in tags
        else "opponent_economic_advantage"
    )
    return {
        "episode_id": row["episode_id"], "opponent": row["opponent"],
        "result": row["result"], "margin": row["margin"],
        "first_divergence_step": row.get("first_large_divergence_step"),
        "primary_cluster": primary, "tags": tags,
        "physical_production_intact": physical_intact,
        "total_revenue": total_revenue, "reference_median_revenue": cohort_revenue,
        "late_period": late, "stranded_value": row.get("final_inventory_value", 0),
        "route_repairs": row.get("route_divergence_count", 0),
    }


def enrich():
    payload = json.loads(DIAGNOSTICS.read_text())
    episodes = payload["episodes"]
    good = sorted(
        [row for row in episodes if row["result"] == "win"],
        key=lambda row: (row["final_money"], row["margin"]), reverse=True,
    )[:max(8, len(episodes) // 4)]
    bad_cut = percentile([row["final_money"] for row in episodes], 0.25)
    bad = [row for row in episodes if row["result"] == "loss" or row["final_money"] <= bad_cut]
    losses = [row for row in episodes if row["result"] == "loss"]
    classified = [classify(row, good) for row in losses]
    counts = Counter(row["primary_cluster"] for row in classified)
    cluster_payload = {
        "schema_version": 1,
        "submission_id": payload["submission_id"],
        "episodes_analyzed": len(episodes),
        "selection": {
            "losses": len(losses), "bottom_quartile_or_loss": len(bad),
            "good_reference_games": len(good), "bottom_quartile_money_cutoff": bad_cut,
        },
        "cluster_counts": dict(counts),
        "episodes": classified,
        "bad_vs_good": {
            "average_money": {
                "bad": statistics.fmean(row["final_money"] for row in bad),
                "good": statistics.fmean(row["final_money"] for row in good),
            },
            "average_margin": {
                "bad": statistics.fmean(row["margin"] for row in bad),
                "good": statistics.fmean(row["margin"] for row in good),
            },
            "average_sale_revenue_bad": product_totals(bad, "sale_revenue"),
            "average_sale_revenue_good": product_totals(good, "sale_revenue"),
            "average_sale_quantity_bad": product_totals(bad, "sale_quantities"),
            "average_sale_quantity_good": product_totals(good, "sale_quantities"),
            "average_harvest_quantity_bad": product_totals(bad, "harvest_quantities"),
            "average_harvest_quantity_good": product_totals(good, "harvest_quantities"),
        },
        "interpretation": (
            "Clusters are repeated observational signatures used to nominate causal tests; "
            "they are not themselves proof that an override has positive action value."
        ),
    }
    CLUSTERS.write_text(json.dumps(cluster_payload, indent=2, sort_keys=True) + "\n")

    # Append a V4-only summary to the detailed report emitted by the exact analyzer.
    lines = REPORT.read_text().rstrip().splitlines()
    lines += [
        "", "## V4 failure clustering", "",
        f"The refreshed corpus contains **{len(episodes)}** valid deployed-V2 games. "
        f"The hard set is {len(losses)} losses plus bottom-quartile games; the reference set "
        f"is the strongest {len(good)} V2 games by realized money.", "",
        "| Cluster | Loss games |", "|---|---:|",
    ]
    for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {name.replace('_', ' ')} | {count} |")
    lines += [
        "", "These labels are hypotheses. V4 promotion depends on paired action counterfactuals, "
        "not on this observational comparison.", "",
    ]
    REPORT.write_text("\n".join(lines))
    return cluster_payload


def main():
    base.MANIFEST = ROOT / "experiments/v3_real_v2_replays/manifest.json"
    base.EXPECTED_BANK = ROOT / "experiments/v2_route_executor.json"
    base.OUTPUT = DIAGNOSTICS
    base.REPORT = REPORT
    base.ROUTE_ID = "super_raw_55463387"
    base.main()
    clusters = enrich()
    print(json.dumps({
        "episodes_analyzed": clusters["episodes_analyzed"],
        "selection": clusters["selection"],
        "cluster_counts": clusters["cluster_counts"],
    }, indent=2))


if __name__ == "__main__":
    main()
