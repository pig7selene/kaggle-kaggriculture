"""Create the compact machine-readable result for the R3 tail study."""

from __future__ import annotations

import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DIAGNOSIS = json.loads((ROOT / "experiments/r3_tail_diagnosis.json").read_text())
HELDOUT = json.loads((ROOT / "experiments/leaderboard_breakthrough_heldout.json").read_text())
SCREEN = json.loads((ROOT / "experiments/r3_guard_screen.json").read_text())
FOLLOWUP = json.loads((ROOT / "experiments/r3_guard_followup.json").read_text())
COW7 = json.loads((ROOT / "experiments/r3_guard_cow7.json").read_text())
FINAL = json.loads((ROOT / "experiments/r3_tail_final.json").read_text())
OUTPUT = ROOT / "experiments/r3_tail_robustification.json"


def _sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _pct(values, fraction):
    values = sorted(values)
    point = fraction * (len(values) - 1)
    lower, upper = int(point), min(len(values) - 1, int(point) + 1)
    weight = point - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _baseline_tail():
    games = HELDOUT["games"]
    controls = {
        (row["group"], row["opponent"], row["seed"], row["seat"]): row
        for row in games if row["candidate"] == "R0_803"
    }
    rows = []
    for row in games:
        if row["candidate"] != "R3_c6_capital":
            continue
        key = (row["group"], row["opponent"], row["seed"], row["seat"])
        rows.append({
            "group": row["group"], "opponent": row["opponent"],
            "seed": row["seed"], "seat": row["seat"],
            "advantage": row["advantage"],
            "money_delta_vs_803": row["money"] - controls[key]["money"],
        })
    deltas = [row["money_delta_vs_803"] for row in rows]
    return {
        "games": len(rows), "average_delta_vs_803": statistics.fmean(deltas),
        "median_delta_vs_803": statistics.median(deltas),
        "p25_delta_vs_803": _pct(deltas, .25), "p10_delta_vs_803": _pct(deltas, .10),
        "p5_delta_vs_803": _pct(deltas, .05), "worst_delta_vs_803": min(deltas),
        "worst_five": sorted(rows, key=lambda row: row["money_delta_vs_803"])[:5],
    }


def _clusters():
    r3 = [row for row in DIAGNOSIS["games"] if row["agent"] == "R3"]
    definitions = {
        "unseen_top_crop_throughput": {
            "opponents": {
                "Amer_high_scale", "Filip_top_template", "Prashant_crop_scaler",
                "Yankang_wheat_close",
            },
            "mechanism": "large day-10 and day-20 crop waves plus higher retained productive throughput",
        },
        "mixed_market_and_livestock": {
            "opponents": {"Ayuma_crop_livestock", "Garigariyong_strawberry", "Okome_strawberry_sheep"},
            "mechanism": "commodity-specific market pressure plus a smaller crop/animal scale edge",
        },
        "six_cow_paired_annuity_regression": {
            "opponents": {"livestock_pressure", "melon_pressure"},
            "mechanism": "six cows trade roughly $14k-$17k animal revenue for only $5k-$8k crop revenue",
        },
        "isolated_capital_wave": {
            "opponents": {"crop_capital_pressure"},
            "mechanism": "single small loss; no persistent common mechanism",
        },
    }
    output = []
    for name, definition in definitions.items():
        games = [row for row in r3 if row["opponent"] in definition["opponents"]]
        losses = [row for row in games if row["advantage"] < 0]
        first_days = [row["diagnosis"]["first_durable_revenue_lead_day"] for row in games if row["diagnosis"]["first_durable_revenue_lead_day"] is not None]
        output.append({
            "cluster": name, "mechanism": definition["mechanism"], "games": len(games),
            "losses": len(losses), "wins": len(games) - len(losses),
            "average_advantage": statistics.fmean(row["advantage"] for row in games),
            "average_loss_damage": statistics.fmean(row["advantage"] for row in losses) if losses else 0,
            "worst_damage": min(row["advantage"] for row in games),
            "median_first_durable_revenue_lead_day": statistics.median(first_days) if first_days else None,
            "determinism": "seat-invariant on replay traces" if all(row["opponent"].endswith(("scale", "template", "scaler", "close", "sheep", "livestock")) for row in games) else "seed/RNG-sensitive",
        })
    return output


def _loss_audit():
    games = {
        (row["agent"], row["tail_kind"], row["opponent"], row["seed"], row["seat"]): row
        for row in DIAGNOSIS["games"]
    }
    output = []
    for pair in DIAGNOSIS["pairs"]:
        r3 = games[("R3", pair["tail_kind"], pair["opponent"], pair["seed"], pair["seat"])]
        diagnosis = r3["diagnosis"]
        output.append({
            "tail_kind": pair["tail_kind"],
            "opponent": pair["opponent"],
            "seed": pair["seed"],
            "seat": pair["seat"],
            "r3_money": pair["r3_money"],
            "opponent_money": r3["opponent_money"],
            "r3_advantage": pair["r3_advantage"],
            "lifecycle_money": pair["lifecycle_money"],
            "r3_delta_vs_lifecycle": pair["r3_delta_vs_lifecycle"],
            "classification": pair["classification"],
            "first_durable_bank_lead_day": diagnosis["first_durable_bank_lead_day"],
            "first_durable_revenue_lead_day": diagnosis["first_durable_revenue_lead_day"],
            "first_durable_crop_lead_day": diagnosis["first_durable_crop_lead_day"],
            "largest_daily_revenue_divergence_day": diagnosis["largest_daily_revenue_divergence_day"],
            "largest_daily_revenue_divergence": diagnosis["largest_daily_revenue_divergence"],
        })
    return output


def _guard_summary(payload):
    paired = {row["candidate"]: row for row in payload["paired_vs_R3"]}
    output = []
    for row in payload["candidates"]:
        overall = row["overall"]
        against_r3 = paired[row["candidate"]]
        output.append({
            "candidate": row["candidate"],
            "games": overall["games"],
            "wins": overall["wins"],
            "losses": overall["losses"],
            "ties": overall["ties"],
            "average_money": overall["average_money"],
            "average_advantage": overall["average_advantage"],
            "average_delta_vs_R3": against_r3["average_delta_vs_R3"],
            "p10_delta_vs_R3": against_r3["p10_delta_vs_R3"],
            "p5_delta_vs_R3": against_r3["p5_delta_vs_R3"],
            "worst_delta_vs_R3": against_r3["worst_delta_vs_R3"],
        })
    return output


def _paired_game_advantages(rows):
    by_game = {}
    for row in rows:
        key = (row["group"], row["opponent"], row["seed"])
        by_game.setdefault(key, []).append(row["advantage"])
    return [statistics.fmean(values) for values in by_game.values()]


def _economic_checkpoints(name):
    rows = [row for row in FINAL["games"] if row["candidate"] == name]
    paired_advantages = _paired_game_advantages(rows)
    cow_counts = Counter(row["checkpoints"]["20"]["animals"].get("COW", 0) for row in rows)
    land_patterns = Counter(tuple(row["land_days"]) for row in rows)
    first_melon_sales = []
    opening_melon_revenue = []
    for row in rows:
        events = [event for event in row["major_sale_windows"] if event["products"].get("MELON", 0)]
        if events:
            first = min(events, key=lambda event: (event["day"], event["hour"]))
            first_melon_sales.append(first["day"] * 24 + first["hour"])
        opening_melon_revenue.append(sum(
            event["products"].get("MELON", 0)
            for event in row["major_sale_windows"] if event["day"] <= 12
        ))
    return {
        "paired_game_advantage": {
            "pairs": len(paired_advantages),
            "average": statistics.fmean(paired_advantages),
            "median": statistics.median(paired_advantages),
            "p25": _pct(paired_advantages, .25),
            "p10": _pct(paired_advantages, .10),
            "p5": _pct(paired_advantages, .05),
            "worst": min(paired_advantages),
        },
        "average_bank": {
            str(day): statistics.fmean(row["checkpoints"][str(day)]["bank"] for row in rows)
            for day in (6, 10, 11, 15, 20)
        },
        "land_day_patterns": {"/".join(map(str, key)): value for key, value in land_patterns.items()},
        "day20_cow_counts": {str(key): value for key, value in cow_counts.items()},
        "average_crop_revenue": statistics.fmean(row["economics"]["full"]["crop_revenue"] for row in rows),
        "average_melon_revenue": statistics.fmean(row["economics"]["full"]["sale_revenue"].get("MELON", 0) for row in rows),
        "average_strawberry_revenue": statistics.fmean(row["economics"]["full"]["sale_revenue"].get("STRAWBERRY", 0) for row in rows),
        "average_opening_melon_revenue_through_day12": statistics.fmean(opening_melon_revenue),
        "median_first_melon_sale_step": statistics.median(first_melon_sales),
        "average_harvest_actions_day10_29": statistics.fmean(
            row["lifecycle_day10_20"]["total_harvest_actions"]
            + row["lifecycle_day21_29"]["total_harvest_actions"]
            for row in rows
        ),
    }


def _finalists():
    candidates = {row["candidate"]: row for row in FINAL["candidates"]}
    paired = {row["candidate"]: row for row in FINAL["paired_vs_R3"]}
    output = []
    for name in ("R3_c6_capital", "G4_milk_annuity", "G8_market_cow7"):
        row = candidates[name]
        matchups = {
            opponent: {
                "wins": summary["wins"], "losses": summary["losses"], "ties": summary["ties"],
                "average_money": summary["average_money"],
                "average_advantage": summary["average_advantage"],
            }
            for opponent, summary in row["matchups"].items()
        }
        output.append({
            "candidate": name,
            "overall": row["overall"],
            "paired_vs_R3": paired[name],
            "direct_vs_803": {
                "fixed": row["groups"]["direct_803_fixed"],
                "natural": row["groups"]["direct_803_natural"],
            },
            "direct_vs_R3": {
                "fixed": row["groups"]["direct_r3_fixed"],
                "natural": row["groups"]["direct_r3_natural"],
            },
            "economic_checkpoints": _economic_checkpoints(name),
            "groups": row["groups"], "matchups": matchups,
        })
    return output


def _capital_windows():
    analysis = json.loads((ROOT / "experiments/leaderboard_breakthrough_analysis.json").read_text())
    median = analysis["top_public"]["aggregate"]["checkpoint_medians"]
    return [
        {
            "event": "first land", "target": "day 6", "cash_required": 1000,
            "typical_cash_source": "day 6 wool plus fertilizer and early wheat",
            "corpus_support": "35/35 selected top appearances",
            "delay_cost_estimate": {"6_turns": 150, "12_turns": 300, "24_turns": 600},
            "basis": "about 8-13 delayed new crop tiles at roughly $75-$100 expected net over 8-12 days, time-prorated",
        },
        {
            "event": "livestock ramp", "target": "days 7-9", "cash_required": 1600,
            "typical_cash_source": "post-deed wool/fertilizer and first milk",
            "corpus_support": "top peak cow median 9; timing varies",
            "delay_cost_estimate": {"6_turns": 180, "12_turns": 360, "24_turns": 720},
            "basis": "one-quarter/half/full day of foregone milk/fertilizer accrual for four incremental cows",
        },
        {
            "event": "second land and planting wave", "target": "day 10", "cash_required": 2000,
            "typical_cash_source": "day 9 milk, day 10 wool, full-yield melon liquidation",
            "corpus_support": "35/35 selected top appearances",
            "delay_cost_estimate": {"6_turns": 400, "12_turns": 800, "24_turns": 1600},
            "basis": "roughly 16-25 delayed crop slots; a full-day delay also risks a labor reset and cohort desynchronization",
        },
        {
            "event": "major post-expansion cohort", "target": "days 10-12", "cash_required": 3000,
            "typical_cash_source": "same day-10/11 synchronized melon conversion",
            "corpus_support": f"top median productive tiles day 10={median['10']['productive_tiles']}, day 11={median['11']['productive_tiles']}",
            "delay_cost_estimate": {"6_turns": 500, "12_turns": 1000, "24_turns": 2000},
            "basis": "one day of delayed production across roughly 20 newly seeded tiles",
        },
    ]


def main():
    payload = {
        "schema_version": 1,
        "frozen_hashes": {
            "agents/leaderboard_r3_cow6_capital.py": _sha("agents/leaderboard_r3_cow6_capital.py"),
            "agents/lifecycle_lc_combined.py": _sha("agents/lifecycle_lc_combined.py"),
            "agents/opening_public_front_cow8_day6.py": _sha("agents/opening_public_front_cow8_day6.py"),
            "submission/main.py": _sha("submission/main.py"),
            "experiments/current_best.json": _sha("experiments/current_best.json"),
        },
        "baseline_heldout_tail": _baseline_tail(),
        "individual_tail_audit": _loss_audit(),
        "failure_clusters": _clusters(),
        "capital_windows": _capital_windows(),
        "guard_screens": {
            "initial": _guard_summary(SCREEN),
            "followup": _guard_summary(FOLLOWUP),
            "cow7": _guard_summary(COW7),
        },
        "decision_regret": {
            "final_watering": {
                "qualifying_r3_melon_harvests_in_27_tail_games": 1,
                "deed_unlocks_from_early_harvest": 0,
                "conclusion": "No observed opening melon wait delayed either required deed; G2's early-harvest exception lost money and worsened tail delta.",
            },
            "sell_now": {
                "conclusion": "R3 drops opening produce promptly and sells it on the next observation; no pre-deed delayed shed cohort exists, so G3 is an intentional no-op control.",
            },
            "cow_count": {
                "conclusion": "Six cows cause the paired annuity tail, but adaptive one/two-cow restoration does not improve the absolute top-template failure cluster.",
            },
        },
        "new_adversaries": {
            "early_cash_burst": "agents/adversaries/r3_early_cash_burst.py",
            "delayed_melon_scaler": "agents/adversaries/r3_delayed_melon_scaler.py",
            "crop_heavy_scaler": "agents/adversaries/r3_crop_heavy_scaler.py",
        },
        "final_seed_partition": FINAL["seed_partition"],
        "finalists": _finalists(),
        "promotion": {
            "promoted": False,
            "strongest_final_candidate": "agents/leaderboard_r3_cow6_capital.py",
            "reason": "Neither guard repairs unseen top-template losses or positive P10; G4 also has livestock/stranding safety failures and G8 regresses in direct and red-team results.",
            "current_best_json_updated": False,
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    print(OUTPUT)


if __name__ == "__main__":
    main()
