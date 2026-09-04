"""Compact, reproducible synthesis of the downloaded public Top-10 corpus.

This script reads the already-frozen V3 Top-10 route bank and the current
Top-50 portfolio metadata.  It deliberately summarizes structural evidence
only; it never uses a replay identity, future state, or final result as a
runtime feature.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parent
TOP10_BANK = ROOT / "experiments/v3_route_bank.json"
TOP10_STABILITY = ROOT / "experiments/v3_route_stability.json"
TOP10_FAMILIES = ROOT / "experiments/v3_route_families.json"
TOP50_BANK = ROOT / "experiments/top50_route_bank.json"
OUT_JSON = ROOT / "experiments/top10_meta_summary.json"
OUT_MD = ROOT / "experiments/top10_meta_summary.md"


def _max_field(states, field, key=None):
    values = []
    for state in states:
        value = state.get(field, {}) if key is None else state.get(field, {}).get(key, 0)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return max(values, default=0.0)


def _route_summary(route):
    states = route["expected_state"]
    milestones = route.get("milestones", {})
    max_crops = {
        crop: int(_max_field(states, "crops", crop))
        for crop in ("WHEAT", "MELON", "STRAWBERRY", "CARROT", "TOMATO")
    }
    max_animals = {
        animal: int(_max_field(states, "animals", animal))
        for animal in ("COW", "SHEEP", "GOOSE")
    }
    return {
        "route_id": route["route_id"],
        "submission_id": int(route["source_submission_id"]),
        "team": route.get("source_team"),
        "family_id": route.get("family_id"),
        "source_rank": None,
        "stability_class": route.get("stability_class"),
        "appearances": int(route.get("appearance_count", 0)),
        "average_source_money": float(route.get("average_source_money", 0.0)),
        "first_land": milestones.get("first_land"),
        "second_land": milestones.get("second_land"),
        "first_melon_sell": milestones.get("first_melon_sell"),
        "first_strawberry_sell": milestones.get("first_strawberry_sell"),
        "last_sell": milestones.get("last_sell"),
        "hands_6": milestones.get("hands_6"),
        "hands_8": milestones.get("hands_8"),
        "hands_10": milestones.get("hands_10"),
        "hands_12": milestones.get("hands_12"),
        "hands_14": milestones.get("hands_14"),
        "cows_4": milestones.get("cows_4"),
        "cows_6": milestones.get("cows_6"),
        "cows_8": milestones.get("cows_8"),
        "max_hands": int(_max_field(states, "hand_count")),
        "max_productive": int(_max_field(states, "productive")),
        "max_crops": max_crops,
        "max_animals": max_animals,
    }


def _mode(values):
    values = [v for v in values if v is not None]
    return Counter(values).most_common(1)[0][0] if values else None


def main():
    top10 = json.loads(TOP10_BANK.read_text())
    stability = json.loads(TOP10_STABILITY.read_text())
    families = json.loads(TOP10_FAMILIES.read_text())
    rank_by_sid = {int(row["submission_id"]): int(row["rank"]) for row in stability["submissions"]}
    routes = [_route_summary(route) for route in top10["routes"]]
    for row in routes:
        row["source_rank"] = rank_by_sid.get(row["submission_id"])
    routes.sort(key=lambda row: (row["source_rank"] or 999, row["submission_id"]))

    def values(key):
        return [row[key] for row in routes if row[key] is not None]

    consensus = {
        "route_count": len(routes),
        "families": len(families["families"]),
        "first_land_mode": _mode(values("first_land")),
        "first_land_range": [min(values("first_land")), max(values("first_land"))],
        "second_land_mode": _mode(values("second_land")),
        "second_land_range": [min(values("second_land")), max(values("second_land"))],
        "max_hands_mode": _mode(values("max_hands")),
        "max_productive_median": statistics.median(values("max_productive")),
        "mixed_cow_sheep": sum(bool(row["max_animals"]["COW"] and row["max_animals"]["SHEEP"]) for row in routes),
        "eight_plus_cows": sum(row["max_animals"]["COW"] >= 8 for row in routes),
        "melon_wave": sum(row["max_crops"]["MELON"] >= 10 for row in routes),
        "strawberry_wave": sum(row["max_crops"]["STRAWBERRY"] >= 25 for row in routes),
        "terminal_sell_step_mode": _mode([row.get("last_sell") for row in routes]),
    }

    # The route bank contains action schedules.  Exact action similarity is a
    # useful guard against mistaking a common skeleton for a common policy.
    raw = {row["route_id"]: next(x for x in top10["routes"] if x["route_id"] == row["route_id"]) for row in routes}
    phase_ranges = {"opening": (0, 144), "first_expansion": (144, 240), "second_expansion": (240, 336), "midgame": (336, 504), "late_game": (504, 648), "liquidation": (648, 719)}
    adaptive = []
    stability_by_sid = {int(row["submission_id"]): row for row in stability["submissions"]}
    for row in routes:
        st = stability_by_sid[row["submission_id"]]
        phase = st.get("stability", {})
        adaptive.append({
            "rank": row["source_rank"], "team": row["team"], "route_id": row["route_id"],
            "classification": st.get("classification"),
            "field_stability": {name: round(float(phase.get(name, {}).get("field", 0.0)), 4) for name in phase_ranges},
            "market_stability": {name: round(float(phase.get(name, {}).get("market", 0.0)), 4) for name in phase_ranges},
        })

    top50 = json.loads(TOP50_BANK.read_text())
    current_ids = {"super_raw_55859516", "super_raw_55886665", "super_raw_55890191"}
    current = [_route_summary(route) for route in top50["routes"] if route["route_id"] in current_ids]
    current_consensus = {
        "route_ids": sorted(current_ids),
        "first_land": sorted(set(row["first_land"] for row in current)),
        "second_land": sorted(set(row["second_land"] for row in current)),
        "max_hands": sorted(set(row["max_hands"] for row in current)),
        "max_cows": sorted(set(row["max_animals"]["COW"] for row in current)),
        "max_sheep": sorted(set(row["max_animals"]["SHEEP"] for row in current)),
    }
    payload = {
        "schema_version": 1,
        "corpus": {"route_count": len(routes), "families": families["family_count"], "development_appearances": 82, "valid_unique_replays": 126},
        "consensus": consensus,
        "routes": routes,
        "adaptive_phase_stability": adaptive,
        "families": families["families"],
        "current_best_parent_summary": current_consensus,
        "interpretation": {
            "shared_meta": [
                "all ten complete routes buy three quadrants by approximately steps 144-160 and 217-264",
                "all ten use a melon wave followed by a strawberry-capable midgame and final selling",
                "all ten scale to roughly 12 hands; the adaptive rank-1 and rank-2 routes vary later actions",
                "mixed cows and sheep are common, but eight-plus cows are not universal",
            ],
            "strongest_stable_top10_family": "v3_family_01 (JALKARNA-like; ranks 3,4,5,7,8,9,10)",
            "safe_adjustment_hypothesis": "add the zero-escape v3_raw_55463387 complete route as a step-1 parent; never splice an adaptive route after state divergence",
            "not_supported": ["rank-1 raw route as a deployable parent because prior tests observed cow escapes", "rank-2 raw route as a generic replacement because prior paired tests were negative", "universal eight-cow or 14-hand rule"],
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")

    lines = [
        "# Top-10 public strategy synthesis", "",
        "This report summarizes the already-downloaded V3 Top-10 corpus; it does not use replay identity or future state as a runtime feature.", "",
        f"Corpus: {len(routes)} selected complete routes, {families['family_count']} structural families, 82 deduplicated development appearances, 126 valid unique replay IDs.", "",
        "## Consensus", "",
        "| pattern | count / range |", "| --- | --- |",
        f"| first extra quadrant | mode {consensus['first_land_mode']} (range {consensus['first_land_range']}) |",
        f"| second extra quadrant | mode {consensus['second_land_mode']} (range {consensus['second_land_range']}) |",
        f"| peak hands | mode {consensus['max_hands_mode']} |",
        f"| mixed cow + sheep | {consensus['mixed_cow_sheep']}/{len(routes)} |",
        f"| eight or more cows | {consensus['eight_plus_cows']}/{len(routes)} |",
        f"| melon wave (10+) | {consensus['melon_wave']}/{len(routes)} |",
        f"| strawberry wave (25+) | {consensus['strawberry_wave']}/{len(routes)} |",
        "",
        "## Route comparison", "",
        "| rank | player | family | land 1/2 | max hands | max cows/sheep | max productive | class |",
        "| ---: | --- | --- | --- | ---: | --- | ---: | --- |",
    ]
    for row in routes:
        lines.append(f"| {row['source_rank']} | {row['team']} | {row['family_id']} | {row['first_land']}/{row['second_land']} | {row['max_hands']} | {row['max_animals']['COW']}/{row['max_animals']['SHEEP']} | {row['max_productive']} | {row['stability_class']} |")
    lines += ["", "## What this means for the current best", "", f"Current Top-50 parents use land {current_consensus['first_land']} → {current_consensus['second_land']}, peak cows {current_consensus['max_cows']}, sheep {current_consensus['max_sheep']}, and peak hands {current_consensus['max_hands']}.", "", "The most defensible missing complete package is the stable JALKARNA-like route (`v3_raw_55463387`): it shares the three-quadrant/melon/strawberry skeleton, has a distinct 160/240 capital calendar, and was previously safety-clean. The rank-1 and rank-2 routes are genuinely adaptive, but their raw transfers were already shown to be unsafe or economically negative; they remain evidence about conditional behavior, not parents to splice.", "", "## Adjustment used", "", "A candidate adds only `v3_raw_55463387` as a fourth complete parent and selects it at step 1 when the opponent's visible opening state is the exact low-bank/four-hand signature of the JALKARNA family. All other states follow the frozen selector. No mid-episode route splice is performed.", ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"json": str(OUT_JSON), "markdown": str(OUT_MD), "consensus": consensus}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
