"""Small economic neighborhood around the successful routed replay policy."""

from __future__ import annotations

import json
import statistics

from benchmark import ROOT, _file_sha256
from run_router_ablation import _run_game, _summary


CANDIDATES = {
    "replay_land_6_10_cow9_h14": ROOT / "agents" / "router_r3_replay_economy.py",
    "two_quadrant": ROOT / "agents" / "router_replay_two_quadrant.py",
    "land_5_9": ROOT / "agents" / "router_replay_land_5_9.py",
    "land_7_11": ROOT / "agents" / "router_replay_land_7_11.py",
    "cow8": ROOT / "agents" / "router_replay_cow8.py",
    "hands12": ROOT / "agents" / "router_replay_hands12.py",
    "mixed_open": ROOT / "agents" / "router_meta_mixed_open.py",
}
OPPONENTS = {
    "current_best": ROOT / "agents" / "animal_c8_day12_land_day11.py",
    "routed_replay_control": ROOT / "agents" / "router_r3_replay_economy.py",
    "gen_land_d8_labor6": ROOT / "agents" / "adversaries" / "gen_land_d8_labor6.py",
    "gen_land_d11_labor7_sell12": ROOT / "agents" / "adversaries" / "gen_land_d11_labor7_sell12.py",
    "gen_cow6_d8": ROOT / "agents" / "adversaries" / "gen_cow6_d8.py",
    "proxy_high_labor": ROOT / "agents" / "proxies" / "high_labor.py",
    "proxy_livestock_crop": ROOT / "agents" / "proxies" / "livestock_crop.py",
}
SEEDS = (13000, 13001)


def _extended_summary(games):
    summary = _summary(games)
    land_days = {}
    for game in games:
        for index, event in enumerate(game["routing"].get("land_use", []), 1):
            land_days.setdefault(index, []).append(event["step"] // 24)
    summary["average_land_days"] = {
        str(index): statistics.fmean(days) for index, days in land_days.items()
    }
    summary["average_labor_spending"] = statistics.fmean(
        game["routing"].get("spending", {}).get("labor", 0) for game in games
    )
    return summary


def main():
    jobs = [
        (candidate, str(path.resolve()), opponent, str(opponent_path.resolve()), seed, seat)
        for candidate, path in CANDIDATES.items()
        for opponent, opponent_path in OPPONENTS.items()
        for seed in SEEDS for seat in (0, 1)
    ]
    games = []
    for index, job in enumerate(jobs, 1):
        games.append(_run_game(job))
        if index % 25 == 0 or index == len(jobs):
            print(f"router neighborhood {index}/{len(jobs)}", flush=True)
    rows = []
    for candidate, path in CANDIDATES.items():
        selected = [game for game in games if game["candidate"] == candidate]
        matchups = {
            opponent: _extended_summary(
                [game for game in selected if game["opponent"] == opponent]
            )
            for opponent in OPPONENTS
        }
        rows.append({
            "candidate": candidate,
            "path": str(path.relative_to(ROOT)),
            "sha256": _file_sha256(path),
            "overall": _extended_summary(selected),
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
        ), reverse=True,
    )
    payload = {
        "schema_version": 1,
        "experiment": "routed_replay_small_neighborhood",
        "seeds": list(SEEDS),
        "both_seats": True,
        "opponents": {name: str(path.relative_to(ROOT)) for name, path in OPPONENTS.items()},
        "games_per_candidate": len(OPPONENTS) * len(SEEDS) * 2,
        "candidates": rows,
        "games": games,
    }
    output = ROOT / "experiments" / "router_neighborhood.json"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(output)
    for row in rows:
        o = row["overall"]
        direct = row["matchups"]["current_best"]
        print(
            row["candidate"], f"{o['wins']}/{o['losses']}/{o['ties']}",
            f"money={o['average_money']:.1f}", f"adv={o['average_advantage']:.1f}",
            f"direct={direct['wins']}/{direct['losses']}/{direct['ties']} "
            f"{direct['average_advantage']:+.1f}",
            f"land={o['average_land_days']}", f"worst={row['worst_opponent']}",
        )


if __name__ == "__main__":
    main()

