"""Fresh final smoke league for the behavior-locked submission package."""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import statistics

from run_shop_router_0909_hardened_final import run_game


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT / "submission/main.py"
OUT = ROOT / "experiments/shop_router_0909_submission_smoke.json"
OPPONENTS = {
    "current_best": ROOT / "agents/top50_distilled/top50_observable_portfolio.py",
    "v2": ROOT / "agents/super_replay_v2/super_backbone_v2.py",
    "k3": ROOT / "agents/v27_k3_weed.py",
    "crop_dusta": ROOT / "agents/top3_tuned/raw_rank2_crop_dusta.py",
}
SEEDS = {"fixed": (1322000, 1322001), "natural": (1322100, 1322101)}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert sha(ROOT / "agents/shop_router_0909_hardened/main.py") == "da5c6df2c71128ce1372a5adaf6d4859f5758e7854b399d6ff634fbca666d8a2"
    jobs = []
    for opponent_name, opponent_path in OPPONENTS.items():
        for mode, seeds in SEEDS.items():
            for seed in seeds:
                for seat in (0, 1):
                    jobs.append(("submission_smoke", "submission", PACKAGE, opponent_name, opponent_path, seed, seat, mode))
    rows = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_game, job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            if len(rows) % 8 == 0 or len(rows) == len(jobs):
                print(f"smoke {len(rows)}/{len(jobs)}", flush=True)
    rows.sort(key=lambda row: (row["opponent"], row["shop_mode"], row["seed"], row["seat"]))
    failures = [row for row in rows if row.get("runtime_error") or row.get("exceptions")]
    valid = [row for row in rows if row not in failures]
    outcomes = Counter(row["outcome"] for row in valid)
    payload = {
        "schema_version": 1,
        "design": "32 fresh games: four strong opponents x fixed/natural x two seeds x both seats.",
        "submission_main_sha256": sha(PACKAGE),
        "games": len(rows),
        "wins": outcomes["win"], "losses": outcomes["loss"], "ties": outcomes["tie"],
        "mean_own_money": statistics.mean(row["own_money"] for row in valid),
        "median_own_money": statistics.median(row["own_money"] for row in valid),
        "mean_advantage": statistics.mean(row["advantage"] for row in valid),
        "worst_advantage": min(row["advantage"] for row in valid),
        "runtime_exceptions": sum(bool(row.get("runtime_error")) for row in rows),
        "agent_exceptions": sum(bool(row.get("exceptions")) for row in rows),
        "livestock_escape_events": sum(len(row.get("livestock_escapes", [])) for row in valid),
        "by_mode": {}, "by_opponent": {}, "rows": rows,
    }
    for field, destination in (("shop_mode", "by_mode"), ("opponent", "by_opponent")):
        for value in sorted({row[field] for row in valid}):
            group = [row for row in valid if row[field] == value]
            counts = Counter(row["outcome"] for row in group)
            payload[destination][value] = {
                "games": len(group), "wins": counts["win"], "losses": counts["loss"], "ties": counts["tie"],
                "mean_own_money": statistics.mean(row["own_money"] for row in group),
                "mean_advantage": statistics.mean(row["advantage"] for row in group),
                "worst_advantage": min(row["advantage"] for row in group),
            }
    OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: payload[key] for key in ("games", "wins", "losses", "ties", "mean_own_money", "mean_advantage", "worst_advantage", "runtime_exceptions", "agent_exceptions", "livestock_escape_events")}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
