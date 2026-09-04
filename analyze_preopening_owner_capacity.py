"""Audit pre-opening capacity in the frozen Top-50 route bank.

This is an offline structural audit.  It does not run games or modify any
agent.  The purpose is to determine whether an extra crop owner can be funded
and hired before day 10 without displacing a route transaction or worker lane.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ROUTE_PATH = ROOT / "experiments/top50_route_bank.json"
OUT_JSON = ROOT / "experiments/preopening_owner_capacity_audit.json"
OUT_MD = ROOT / "experiments/preopening_owner_capacity_audit.md"


def _op(order):
    return order[0] if isinstance(order, list) and order else ""


def _fib(index):
    a, b = 1, 1
    for _ in range(max(0, int(index))):
        a, b = b, a + b
    return a


def _boundary(row, step):
    state = row["expected_state"][str(step)] if isinstance(row["expected_state"], dict) and str(step) in row["expected_state"] else row["expected_state"][step]
    action = row["consensus_actions"][step]
    market = list(action.get("market", []))
    return {
        "step": step,
        "day": int(state.get("day", step // 24)),
        "money": float(state.get("money", 0.0)),
        "hands": int(state.get("hand_count", len(state.get("hands", [])))),
        "quadrants": len(state.get("quadrants", [])),
        "productive": int(state.get("productive", 0)),
        "market_orders": len(market),
        "hire_orders": sum(_op(order) == "HIRE" for order in market),
        "land_orders": sum(_op(order) == "BUY_LAND" for order in market),
        "animal_orders": sum(_op(order) == "BUY_ANIMAL" for order in market),
        "seed_orders": sum(_op(order) == "BUY_SEED" for order in market),
        "sell_orders": sum(_op(order) == "SELL" for order in market),
        "pass_units": sum(_op(value) == "PASS" for value in [action.get("farmer", ["PASS"]), *action.get("hands", [])]),
    }


def _route_report(row):
    # Day-boundary snapshots through day 10 plus every market turn in the
    # opening.  A route's expected_state is indexed by integer steps in the
    # manifest, but tolerate string-keyed JSON for portability.
    boundaries = [_boundary(row, day * 24) for day in range(0, 11)]
    daily = []
    for day in range(0, 11):
        samples = [_boundary(row, step) for step in range(day * 24, min((day + 1) * 24, 264))]
        daily.append({
            "day": day,
            "max_hands": max((s["hands"] for s in samples), default=0),
            "max_pass_units": max((s["pass_units"] for s in samples), default=0),
            "mean_pass_units": sum(s["pass_units"] for s in samples) / len(samples) if samples else 0.0,
            "max_productive": max((s["productive"] for s in samples), default=0),
        })
    opening_steps = []
    for step in range(1, 11 * 24):
        action = row["consensus_actions"][step]
        market = list(action.get("market", []))
        if not market:
            continue
        b = _boundary(row, step)
        b["extra_slot_for_seed_plus_hire"] = len(market) <= 8
        b["extra_slot_for_hire"] = len(market) <= 9
        b["orders"] = market
        opening_steps.append(b)
    first_land = next((step for step in range(240) if _op(row["consensus_actions"][step].get("market", [])[0] if row["consensus_actions"][step].get("market") else []) == "BUY_LAND"), None)
    # Use the route milestone when available; the action scan above is only a
    # consistency check because BUY_LAND is not necessarily slot zero.
    first_land = row.get("milestones", {}).get("first_land", first_land)
    return {
        "route_id": row["route_id"],
        "source_team": row.get("source_team"),
        "source_final_money": row.get("source_final_money"),
        "first_land_step": first_land,
        "boundaries": boundaries,
        "daily": daily,
        "opening_market_turns": opening_steps,
        "opening_market_turn_count": len(opening_steps),
        "turns_with_seed_plus_hire_slot": sum(bool(b.get("extra_slot_for_seed_plus_hire")) for b in opening_steps),
        "turns_with_hire_slot": sum(bool(b.get("extra_slot_for_hire")) for b in opening_steps),
        "turns_with_pass_unit": sum(int(b.get("pass_units", 0)) > 0 for b in opening_steps),
    }


def _render(payload):
    rows = payload["routes"]
    lines = [
        "# Pre-opening owner capacity audit",
        "",
        "Date: 2026-09-02",
        "",
        "This offline audit reads the frozen Top-50 route bank only.  It does",
        "not run a simulator and does not alter any strategy or submission.",
        "",
        "## Route-level capacity",
        "",
        "| route | team | first land | max hands d2 | max hands d6 | max hands d10 | seed+hire slots (d0–10) | hire slots | PASS market turns |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        by_day = {int(b["day"]): b for b in row["daily"]}
        lines.append(
            f"| {row['route_id']} | {row.get('source_team')} | {row.get('first_land_step')} "
            f"| {by_day.get(2, {}).get('max_hands', 0)} | {by_day.get(6, {}).get('max_hands', 0)} "
            f"| {by_day.get(10, {}).get('max_hands', 0)} | {row['turns_with_seed_plus_hire_slot']} "
            f"| {row['turns_with_hire_slot']} | {row['turns_with_pass_unit']} |"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "The route bank shows a recurring structural constraint: the initial NW",
        "quadrant is effectively full by day 2, so a pre-opening crop owner must",
        "reserve a future-quadrant tile before first land.  An additional hand",
        "also needs a daily market slot; a turn with ten existing orders cannot",
        "fund it without replacing a route purchase or hire.  PASS counts are",
        "only a necessary condition, not proof of safe execution, because the",
        "route's crop/animal obligations can still occupy those units on later",
        "turns.",
        "",
        "The next complete-owner experiment should therefore be restricted to a",
        "route/day window that has both a reserved future tile and recurring",
        "seed-plus-hire slots.  If no route provides that window through the",
        "entire lifecycle, adding a cohort requires a coherent route rewrite",
        "rather than an overlay.",
        "",
        "## Reproducibility",
        "",
        "- `experiments/preopening_owner_capacity_audit.json`",
        "- `analyze_preopening_owner_capacity.py`",
    ]
    return "\n".join(lines) + "\n"


def main():
    source = json.loads(ROUTE_PATH.read_text())
    routes = [_route_report(row) for row in source.get("routes", [])]
    payload = {
        "schema_version": 1,
        "source": str(ROUTE_PATH.relative_to(ROOT)),
        "scope": "steps 0-263, day-boundary expected states and market turns",
        "routes": routes,
        "summary": {
            "route_count": len(routes),
            "routes_with_seed_plus_hire_slot": sum(r["turns_with_seed_plus_hire_slot"] > 0 for r in routes),
            "routes_with_hire_slot": sum(r["turns_with_hire_slot"] > 0 for r in routes),
            "routes_with_no_seed_plus_hire_slot": sum(r["turns_with_seed_plus_hire_slot"] == 0 for r in routes),
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    OUT_MD.write_text(_render(payload))
    print(OUT_JSON)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
