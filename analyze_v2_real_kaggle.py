"""Diagnose deployed V1 public episodes against Ricardo's expected trajectory."""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

from analyze_super_replays import _counts, _timeline
from analyze_top_player_replays import _appearance_summary
from analyze_v27_routes import normalized_action, state_anchor


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "experiments/v2_real_kaggle_replays/manifest.json"
EXPECTED_BANK = ROOT / "experiments/super_replay_route_executor.json"
OUTPUT = ROOT / "experiments/v2_real_kaggle_diagnostics.json"
REPORT = ROOT / "experiments/v2_real_kaggle_diagnostics.md"
ROUTE_ID = "super_raw_55459817"
CHECKPOINTS = tuple(range(0, 719, 24)) + (718,)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _digest(value):
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _counter_l1(left, right):
    return sum(abs(int(left.get(key, 0)) - int(right.get(key, 0))) for key in set(left) | set(right))


def _inventory(obs):
    private = obs["private"]
    carried = Counter()
    for row in private.get("inventories", []):
        carried.update({key: int(value) for key, value in row.items()})
    shed = {key: int(value) for key, value in private.get("shed", {}).items() if value}
    seeds = {key: int(value) for key, value in private.get("seeds", {}).items() if value}
    return shed, seeds, dict(carried)


def _worker_error(actual, expected):
    count = min(len(actual), len(expected))
    distance = sum(abs(actual[i][0] - expected[i][0]) + abs(actual[i][1] - expected[i][1]) for i in range(count))
    return distance + 10 * abs(len(actual) - len(expected))


def _state_error(actual, expected):
    bank_scale = abs(float(actual["money_delta"])) / 1000
    return (
        bank_scale + 3 * abs(actual["hand_delta"]) + 8 * abs(actual["quadrant_delta"])
        + 2 * actual["animal_l1"] + actual["crop_l1"] / 4
        + actual["inventory_l1"] / 15 + actual["worker_position_l1"] / 20
    )


def _episode(row, expected):
    replay = json.loads((ROOT / row["replay_path"]).read_text())
    seat = int(row["seat"])
    timeline, errors = _timeline(replay, seat)
    final_money = [float(value["reward"]) for value in replay["steps"][-1]]
    economy = _appearance_summary(row["episode_id"], seat, replay["info"]["TeamNames"], timeline, final_money)
    checkpoints = []
    first_large = None
    trajectory_error = []
    repair_like_steps = []
    action_mismatches = []
    utilization = Counter()
    for step in range(719):
        obs = replay["steps"][step][seat]["observation"]
        me = obs["farms"][seat]
        actual_counts = _counts(me)
        target = expected[step]
        shed, seeds, carried = _inventory(obs)
        target_carried = Counter()
        for inventory in target.get("inventories", []):
            target_carried.update(inventory)
        delta = {
            "step": step, "day": int(obs["day"]), "hour": int(obs["hour"]),
            "expected_money": float(target.get("money", me["money"])), "actual_money": float(me["money"]),
            "money_delta": float(me["money"]) - float(target.get("money", me["money"])),
            "expected_hands": int(target.get("hand_count", 0)), "actual_hands": len(me.get("hands", [])),
            "hand_delta": len(me.get("hands", [])) - int(target.get("hand_count", 0)),
            "expected_quadrants": len(target.get("quadrants", [])), "actual_quadrants": len(me.get("unlocked_quadrants", [])),
            "quadrant_delta": len(me.get("unlocked_quadrants", [])) - len(target.get("quadrants", [])),
            "expected_animals": target.get("animals", {}), "actual_animals": actual_counts["animals"],
            "animal_l1": _counter_l1(actual_counts["animals"], target.get("animals", {})),
            "expected_crops": target.get("crops", {}), "actual_crops": actual_counts["crops"],
            "crop_l1": _counter_l1(actual_counts["crops"], target.get("crops", {})),
            "expected_cohorts": target.get("cohorts", target.get("crop_cohorts", {})), "actual_cohorts": actual_counts["cohorts"],
            "cohort_l1": _counter_l1(actual_counts["cohorts"], target.get("cohorts", target.get("crop_cohorts", {}))),
            "expected_shed": {k: v for k, v in target.get("shed", {}).items() if v}, "actual_shed": shed,
            "expected_seeds": {k: v for k, v in target.get("seeds", {}).items() if v}, "actual_seeds": seeds,
            "actual_carried": carried, "expected_carried": dict(target_carried),
            "inventory_l1": _counter_l1(shed, target.get("shed", {})) + _counter_l1(carried, target_carried),
            "expected_farmer": target.get("farmer"), "actual_farmer": list(me["farmer"]),
            "expected_worker_positions": target.get("hands", []), "actual_worker_positions": [list(p) for p in me.get("hands", [])],
            "worker_position_l1": _worker_error(me.get("hands", []), target.get("hands", [])),
            "expected_productive": int(target.get("productive", 0)), "actual_productive": int(actual_counts["productive"]),
            "productive_delta": int(actual_counts["productive"]) - int(target.get("productive", 0)),
            "weeds": int(actual_counts["weeds"]),
        }
        delta["trajectory_error"] = _state_error(delta, target)
        trajectory_error.append(delta["trajectory_error"])
        if first_large is None and step >= 24 and delta["trajectory_error"] >= 10:
            first_large = step
        if step in CHECKPOINTS:
            checkpoints.append(delta)
        source_action = expected[step].get("requested_action")
        actual_action = normalized_action(replay, seat, step)
        for request in [actual_action["farmer"], *actual_action["hands"]]:
            op = request[0] if request else "PASS"
            utilization["slots"] += 1
            utilization["idle"] += op == "PASS"
            utilization["movement"] += op in {"NORTH", "SOUTH", "EAST", "WEST"}
            utilization["productive"] += op in {
                "PLANT", "WATER", "HARVEST", "FERTILIZE", "DIG", "BUILD_COOP",
                "BUILD_PASTURE", "FEED", "CARE", "COLLECT_FERTILIZER", "PICKUP", "DROP", "PLACE",
            }
        if source_action is not None and actual_action != source_action:
            action_mismatches.append(step)
        # K3's observable signature: a blocking weed followed by DIG where the
        # backbone requested a plant/structure action.  Route payload actions
        # are used below after they are attached by the caller.
    route_actions = _episode.route_actions
    for step in range(719):
        actual_action = normalized_action(replay, seat, step)
        expected_action = route_actions[step]
        for actual, planned in zip([actual_action["farmer"], *actual_action["hands"]], [expected_action["farmer"], *expected_action["hands"]]):
            if actual and planned and actual[0] == "DIG" and planned[0] in {"PLANT", "BUILD_COOP", "BUILD_PASTURE"}:
                repair_like_steps.append(step)
                break
    result = "win" if final_money[seat] > final_money[1-seat] else "loss" if final_money[seat] < final_money[1-seat] else "tie"
    margin = final_money[seat] - final_money[1-seat]
    final_inventory_value = 0
    final_obs = replay["steps"][-1][seat]["observation"]
    quantities = Counter(final_obs["private"].get("shed", {}))
    for inv in final_obs["private"].get("inventories", []):
        quantities.update(inv)
    for product, quantity in quantities.items():
        final_inventory_value += int(quantity) * int(final_obs["market"]["prices"].get(product, 0))
    return {
        "episode_id": row["episode_id"], "seed": row["seed"], "seat": seat,
        "opponent": replay["info"]["TeamNames"][1-seat], "result": result,
        "final_money": final_money[seat], "opponent_money": final_money[1-seat], "margin": margin,
        "bucket": None, "first_large_divergence_step": first_large,
        "average_trajectory_error": statistics.fmean(trajectory_error),
        "max_trajectory_error": max(trajectory_error), "checkpoints": checkpoints,
        "route_action_divergent_steps": repair_like_steps,
        "route_divergence_count": len(set(repair_like_steps)),
        "financial_reconstruction_mismatches": errors,
        "economy": {key: economy[key] for key in (
            "land_purchase_days", "max_hands", "peak_animals", "peak_crops", "max_productive_tiles",
            "seed_spending", "feed_spending", "animal_spending", "harvest_quantities",
            "sale_quantities", "sale_revenue", "total_sale_revenue", "premium_holding", "investment_events",
        )},
        "daily": timeline, "final_inventory_value": final_inventory_value,
        "worker_utilization": {
            "total_action_slots": utilization["slots"],
            "productive_action_slots": utilization["productive"],
            "movement_action_slots": utilization["movement"],
            "idle_action_slots": utilization["idle"],
            "productive_rate": utilization["productive"] / max(1, utilization["slots"]),
            "movement_rate": utilization["movement"] / max(1, utilization["slots"]),
            "idle_rate": utilization["idle"] / max(1, utilization["slots"]),
        },
        "action_hash": _digest([normalized_action(replay, seat, step) for step in range(719)]),
    }


def _mean(rows, getter):
    return statistics.fmean(getter(row) for row in rows) if rows else None


def _aggregate(label, rows):
    if not rows:
        return {"label": label, "games": 0}
    products = sorted({p for row in rows for p in row["economy"]["sale_revenue"]})
    return {
        "label": label, "games": len(rows),
        "wins": sum(row["result"] == "win" for row in rows), "losses": sum(row["result"] == "loss" for row in rows),
        "average_final_money": _mean(rows, lambda r: r["final_money"]),
        "average_margin": _mean(rows, lambda r: r["margin"]),
        "median_margin": statistics.median(row["margin"] for row in rows),
        "average_trajectory_error": _mean(rows, lambda r: r["average_trajectory_error"]),
        "average_first_large_divergence_step": _mean([r for r in rows if r["first_large_divergence_step"] is not None], lambda r: r["first_large_divergence_step"]),
        "average_max_productive": _mean(rows, lambda r: r["economy"]["max_productive_tiles"]),
        "average_harvests": {p: _mean(rows, lambda r, p=p: r["economy"]["harvest_quantities"].get(p, 0)) for p in products},
        "average_revenue": {p: _mean(rows, lambda r, p=p: r["economy"]["sale_revenue"].get(p, 0)) for p in products},
        "average_route_repairs": _mean(rows, lambda r: r["route_divergence_count"]),
        "average_final_inventory_value": _mean(rows, lambda r: r["final_inventory_value"]),
        "average_worker_productive_rate": _mean(rows, lambda r: r["worker_utilization"]["productive_rate"]),
        "average_worker_movement_rate": _mean(rows, lambda r: r["worker_utilization"]["movement_rate"]),
        "average_worker_idle_rate": _mean(rows, lambda r: r["worker_utilization"]["idle_rate"]),
    }


def _checkpoint_group(rows, step):
    points = []
    for row in rows:
        point = next((p for p in row["checkpoints"] if p["step"] == step), None)
        if point:
            points.append(point)
    keys = ("money_delta", "hand_delta", "quadrant_delta", "animal_l1", "crop_l1", "cohort_l1", "inventory_l1", "worker_position_l1", "productive_delta", "trajectory_error")
    return {key: statistics.fmean(point[key] for point in points) for key in keys} if points else {}


def main():
    manifest = json.loads(MANIFEST.read_text())
    bank = json.loads(EXPECTED_BANK.read_text())
    route = next(row for row in bank["routes"] if row["route_id"] == ROUTE_ID)
    _episode.route_actions = route["consensus_actions"]
    expected = route["expected_state"]
    # Add the exact requested action to expected state only in memory.
    for step in range(719):
        expected[step]["requested_action"] = route["consensus_actions"][step]
    episodes = []
    for index, row in enumerate(manifest["episodes"], 1):
        if row["valid"] and row["seat"] in (0, 1):
            episodes.append(_episode(row, expected))
        if index % 10 == 0:
            print(f"diagnosed {index}/{len(manifest['episodes'])}", flush=True)
    margins = sorted(row["margin"] for row in episodes if row["result"] == "win")
    low_cut = statistics.quantiles(margins, n=4)[0] if len(margins) >= 4 else 0
    money = [row["final_money"] for row in episodes]
    low_money_cut = statistics.quantiles(money, n=10)[0]
    high_money_cut = statistics.quantiles(money, n=10)[-1]
    for row in episodes:
        if row["result"] == "loss": row["bucket"] = "loss"
        elif row["final_money"] <= low_money_cut: row["bucket"] = "unusually_low_money"
        elif row["margin"] <= low_cut: row["bucket"] = "low_margin_win"
        elif row["final_money"] >= high_money_cut: row["bucket"] = "high_money"
        else: row["bucket"] = "normal_win"
    buckets = {name: [row for row in episodes if row["bucket"] == name] for name in ("loss", "unusually_low_money", "low_margin_win", "normal_win", "high_money")}
    aggregates = {name: _aggregate(name, rows) for name, rows in buckets.items()}
    comparison_steps = (96, 144, 160, 192, 240, 264, 336, 480, 600, 696, 718)
    checkpoint_comparison = {
        str(step): {name: _checkpoint_group(rows, step) for name, rows in buckets.items() if rows}
        for step in comparison_steps
    }
    losses = buckets["loss"]
    repeated = []
    if losses:
        for category, predicate in (
            ("capital_shortfall", lambda p: p["money_delta"] < -1500),
            ("delayed_land", lambda p: p["quadrant_delta"] < 0),
            ("delayed_hire", lambda p: p["hand_delta"] < -2),
            ("livestock_drift", lambda p: p["animal_l1"] >= 2),
            ("crop_cohort_desynchronization", lambda p: p["cohort_l1"] >= 12),
            ("worker_position_drift", lambda p: p["worker_position_l1"] >= 30),
            ("productive_tile_deficit", lambda p: p["productive_delta"] <= -8),
            ("endgame_stranding", lambda p: False),
        ):
            count = sum(any(predicate(point) for point in row["checkpoints"]) for row in losses)
            if category == "endgame_stranding": count = sum(row["final_inventory_value"] > 500 for row in losses)
            repeated.append({"category": category, "loss_games": count, "loss_share": count / len(losses)})
    output = {
        "schema_version": 1, "submission_id": manifest["submission_id"],
        "route_id": ROUTE_ID, "replays_analyzed": len(episodes),
        "wins": sum(row["result"] == "win" for row in episodes),
        "losses": sum(row["result"] == "loss" for row in episodes),
        "ties": sum(row["result"] == "tie" for row in episodes),
        "low_margin_cutoff": low_cut, "low_money_cutoff": low_money_cut, "high_money_cutoff": high_money_cut,
        "aggregates": aggregates, "checkpoint_comparison": checkpoint_comparison,
        "repeated_failure_modes": sorted(repeated, key=lambda r: (-r["loss_games"], r["category"])),
        "episodes": episodes,
        "financial_reconstruction_mismatch_count": sum(len(row["financial_reconstruction_mismatches"]) for row in episodes),
    }
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    lines = [
        "# V2 real Kaggle diagnostics", "",
        f"Submission `{manifest['submission_id']}`: {len(episodes)} public episodes, "
        f"{output['wins']} wins / {output['losses']} losses / {output['ties']} ties.", "",
        "## Outcome buckets", "",
        "| Bucket | Games | Avg money | Avg margin | Avg trajectory error | Avg productive peak |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, row in aggregates.items():
        if row["games"]:
            lines.append(f"| {name} | {row['games']} | {row['average_final_money']:,.0f} | {row['average_margin']:+,.0f} | {row['average_trajectory_error']:.2f} | {row['average_max_productive']:.1f} |")
    lines += ["", "## Repeated loss signatures", "", "| Category | Loss games | Share |", "|---|---:|---:|"]
    for row in output["repeated_failure_modes"]:
        lines.append(f"| {row['category']} | {row['loss_games']} | {row['loss_share']:.1%} |")
    lines += ["", "## Losses", "", "| Episode | Opponent | Seat | Money | Opponent | Margin | First large divergence | Repairs | Final inventory value |", "|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in sorted(losses, key=lambda r: r["margin"]):
        lines.append(f"| {row['episode_id']} | {row['opponent']} | {row['seat']} | {row['final_money']:,.0f} | {row['opponent_money']:,.0f} | {row['margin']:+,.0f} | {row['first_large_divergence_step']} | {row['route_divergence_count']} | {row['final_inventory_value']:,.0f} |")
    lines += ["", "The JSON artifact contains all day-by-day ledgers and checkpoint-level expected/actual state comparisons.", ""]
    REPORT.write_text("\n".join(lines))
    print(OUTPUT, REPORT)
    print(json.dumps({k: output[k] for k in ("replays_analyzed", "wins", "losses", "ties", "financial_reconstruction_mismatch_count", "repeated_failure_modes")}, indent=2))


if __name__ == "__main__":
    main()
