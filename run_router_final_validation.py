"""Fresh-seed high-scale confirmation for the large-scale router finalists."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmark import ROOT, _file_sha256
from run_router_ablation import _run_game, _summary


CANDIDATES = {
    "frozen_current_best": ROOT / "agents" / "animal_c8_day12_land_day11.py",
    "routed_replay_cow9_h14": ROOT / "agents" / "router_r3_replay_economy.py",
    "routed_replay_cow8_h14": ROOT / "agents" / "router_replay_cow8.py",
    "routed_replay_cow9_h12": ROOT / "agents" / "router_replay_hands12.py",
}

OPPONENTS = {
    "current_best": ROOT / "agents" / "animal_c8_day12_land_day11.py",
    "old_router_replay": ROOT / "agents" / "replay_meta_full_schedule.py",
    "mixed_replay_open": ROOT / "agents" / "router_meta_mixed_open.py",
    "early_land_d8": ROOT / "agents" / "adversaries" / "gen_land_d8_labor6.py",
    "land_labor_d11": ROOT / "agents" / "adversaries" / "gen_land_d11_labor7_sell12.py",
    "early_cow_d8": ROOT / "agents" / "adversaries" / "gen_cow6_d8.py",
    "proxy_high_labor": ROOT / "agents" / "proxies" / "high_labor.py",
    "proxy_livestock_crop": ROOT / "agents" / "proxies" / "livestock_crop.py",
}


def _candidate_result(name, games):
    matchups = {
        opponent: _summary([game for game in games if game["opponent"] == opponent])
        for opponent in OPPONENTS
    }
    return {
        "candidate": name,
        "path": str(CANDIDATES[name].relative_to(ROOT)),
        "sha256": _file_sha256(CANDIDATES[name]),
        "overall": _summary(games),
        "matchups": matchups,
        "worst_opponent": min(
            matchups,
            key=lambda opponent: (
                matchups[opponent]["score_rate"],
                matchups[opponent]["average_advantage"],
            ),
        ),
    }


def _run_candidate(name, seeds):
    path = CANDIDATES[name]
    jobs = [
        (name, str(path.resolve()), opponent, str(opponent_path.resolve()), seed, seat)
        for opponent, opponent_path in OPPONENTS.items()
        for seed in seeds
        for seat in (0, 1)
    ]
    games = []
    for index, job in enumerate(jobs, 1):
        games.append(_run_game(job))
        if index % 32 == 0 or index == len(jobs):
            print(f"{name} {index}/{len(jobs)}", flush=True)
    row = _candidate_result(name, games)
    part_dir = ROOT / "experiments" / "router_final_parts"
    part_dir.mkdir(parents=True, exist_ok=True)
    output = part_dir / f"{name}.json"
    output.write_text(json.dumps({
        "schema_version": 1,
        "experiment": "large_scale_router_fresh_confirmation_part",
        "seeds": seeds,
        "both_seats": True,
        "opponents": {
            opponent: str(path.relative_to(ROOT)) for opponent, path in OPPONENTS.items()
        },
        "candidate": row,
    }, indent=2) + "\n", encoding="utf-8")
    print(output)
    return row


def _combine(seeds):
    part_dir = ROOT / "experiments" / "router_final_parts"
    rows = []
    for name in CANDIDATES:
        path = part_dir / f"{name}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["seeds"] != seeds:
            raise RuntimeError(f"seed mismatch in {path}")
        rows.append(payload["candidate"])
    rows.sort(
        key=lambda row: (
            row["overall"]["score_rate"], row["overall"]["average_money"]
        ),
        reverse=True,
    )
    payload = {
        "schema_version": 1,
        "experiment": "large_scale_router_fresh_confirmation",
        "seeds": seeds,
        "both_seats": True,
        "games_per_candidate": len(OPPONENTS) * len(seeds) * 2,
        "opponents": {
            opponent: str(path.relative_to(ROOT)) for opponent, path in OPPONENTS.items()
        },
        "candidates": rows,
    }
    output = ROOT / "experiments" / "router_final_validation.json"
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(output)
    for row in rows:
        overall = row["overall"]
        direct = row["matchups"]["current_best"]
        print(
            row["candidate"],
            f"{overall['wins']}/{overall['losses']}/{overall['ties']}",
            f"money={overall['average_money']:.1f}",
            f"adv={overall['average_advantage']:+.1f}",
            f"p10={overall['p10_seed_advantage']:+.1f}",
            f"direct={direct['wins']}/{direct['losses']}/{direct['ties']} "
            f"{direct['average_advantage']:+.1f}",
            f"worst={row['worst_opponent']}",
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", choices=tuple(CANDIDATES) + ("all",), default="all")
    parser.add_argument("--seed-start", type=int, default=13100)
    parser.add_argument("--seeds", type=int, default=16)
    parser.add_argument("--combine", action="store_true")
    args = parser.parse_args()
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    if args.combine:
        _combine(seeds)
        return
    names = tuple(CANDIDATES) if args.candidate == "all" else (args.candidate,)
    for name in names:
        _run_candidate(name, seeds)


if __name__ == "__main__":
    main()
