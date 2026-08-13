"""Controlled mixed-livestock screen after the scalable router ablation."""

from __future__ import annotations

import json
import statistics

from benchmark import ROOT, _file_sha256
from run_router_ablation import _run_game, _summary


CANDIDATES = {
    "R3_cow9_base12": ROOT / "agents" / "router_r3_replay_economy.py",
    "cow9_base10": ROOT / "agents" / "router_meta_cow_only.py",
    "sheep13_only": ROOT / "agents" / "router_meta_sheep_only.py",
    "cow1_sheep4_open_w5": ROOT / "agents" / "router_meta_mixed_open.py",
    "cow1_sheep4_open_w6": ROOT / "agents" / "router_meta_mixed_open_w6.py",
    "sheep5_then_cows": ROOT / "agents" / "router_meta_sheep_to_cow.py",
    "mixed_scaled_9c6s": ROOT / "agents" / "router_meta_mixed_throughout.py",
}
OPPONENTS = {
    "current_best": ROOT / "agents" / "animal_c8_day12_land_day11.py",
    "R3_router_replay": ROOT / "agents" / "router_r3_replay_economy.py",
    "gen_land_d8_labor6": ROOT / "agents" / "adversaries" / "gen_land_d8_labor6.py",
    "gen_cow6_d8": ROOT / "agents" / "adversaries" / "gen_cow6_d8.py",
    "proxy_livestock_crop": ROOT / "agents" / "proxies" / "livestock_crop.py",
}
SEEDS = (12950, 12951)


def _economic_summary(games):
    base = _summary(games)
    revenue = {
        product: statistics.fmean(game["sale_revenue"].get(product, 0) for game in games)
        for product in ("MILK", "WOOL", "FERTILIZER")
    }
    feed_cost = statistics.fmean(
        game["routing"].get("spending", {}).get("products", {}).get("WHEAT", 0)
        for game in games
    )
    animal_spend = statistics.fmean(
        sum(game["routing"].get("spending", {}).get("animals", {}).values())
        for game in games
    )
    paybacks = [
        game["routing"].get("animal_payback_day")
        for game in games
        if game["routing"].get("animal_payback_day") is not None
    ]
    service_actions = []
    for game in games:
        service_actions.append(sum(
            profile.get("responsibilities", {}).get("animal", 0)
            for profile in game["routing"].get("worker_profiles", [])
        ))
    base.update({
        "average_milk_revenue": revenue["MILK"],
        "average_wool_revenue": revenue["WOOL"],
        "average_fertilizer_revenue": revenue["FERTILIZER"],
        "average_feed_cost": feed_cost,
        "average_animal_purchase_spending": animal_spend,
        "average_animal_net_cash": (
            revenue["MILK"] + revenue["WOOL"] + revenue["FERTILIZER"]
            - feed_cost - animal_spend
        ),
        "average_animal_service_actions": statistics.fmean(service_actions),
        "median_animal_payback_day": statistics.median(paybacks) if paybacks else None,
        "payback_observations": len(paybacks),
    })
    return base


def main():
    games = []
    jobs = [
        (candidate, str(path.resolve()), opponent, str(opponent_path.resolve()), seed, seat)
        for candidate, path in CANDIDATES.items()
        for opponent, opponent_path in OPPONENTS.items()
        for seed in SEEDS for seat in (0, 1)
    ]
    for index, job in enumerate(jobs, 1):
        games.append(_run_game(job))
        if index % 20 == 0 or index == len(jobs):
            print(f"mixed livestock {index}/{len(jobs)}", flush=True)
    rows = []
    for candidate, path in CANDIDATES.items():
        selected = [game for game in games if game["candidate"] == candidate]
        matchups = {
            opponent: _economic_summary(
                [game for game in selected if game["opponent"] == opponent]
            )
            for opponent in OPPONENTS
        }
        rows.append({
            "candidate": candidate,
            "path": str(path.relative_to(ROOT)),
            "sha256": _file_sha256(path),
            "overall": _economic_summary(selected),
            "matchups": matchups,
            "worst_opponent": min(
                matchups,
                key=lambda name: (
                    matchups[name]["score_rate"], matchups[name]["average_advantage"]
                ),
            ),
        })
    rows.sort(
        key=lambda row: (
            row["overall"]["score_rate"], row["overall"]["average_money"]
        ),
        reverse=True,
    )
    payload = {
        "schema_version": 1,
        "experiment": "mixed_livestock_router_screen",
        "seeds": list(SEEDS),
        "both_seats": True,
        "opponents": {name: str(path.relative_to(ROOT)) for name, path in OPPONENTS.items()},
        "games_per_candidate": len(OPPONENTS) * len(SEEDS) * 2,
        "candidates": rows,
        "games": games,
    }
    output = ROOT / "experiments" / "mixed_livestock_router_screen.json"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(output)
    for row in rows:
        o = row["overall"]
        print(
            row["candidate"], f"{o['wins']}/{o['losses']}/{o['ties']}",
            f"money={o['average_money']:.1f}", f"adv={o['average_advantage']:.1f}",
            f"milk={o['average_milk_revenue']:.1f}", f"wool={o['average_wool_revenue']:.1f}",
            f"fert={o['average_fertilizer_revenue']:.1f}", f"net={o['average_animal_net_cash']:.1f}",
            f"payback={o['median_animal_payback_day']}", f"worst={row['worst_opponent']}",
        )


if __name__ == "__main__":
    main()

