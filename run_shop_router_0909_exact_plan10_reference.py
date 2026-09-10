"""Fresh Exact controls for the locked Plan-10 validation matrix."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
import json

from run_shop_router_0909_hardened_final import (
    EXACT,
    OPPONENTS,
    OUT,
    PLAN10_FIXED_SEEDS,
    PLAN10_NATURAL_SEEDS,
    ROOT,
    run_game,
    sha,
)


REFERENCE_OUT = ROOT / "experiments/shop_router_0909_exact_plan10_reference_raw.json"


def build_jobs():
    jobs = []
    for opponent_name in ("current_best", "v2", "k3", "crop_dusta"):
        for seed in PLAN10_FIXED_SEEDS:
            for seat in (0, 1):
                jobs.append((
                    "plan10_exact_reference", "exact", EXACT, opponent_name,
                    OPPONENTS[opponent_name], seed, seat, "fixed_plan10",
                ))
    for opponent_name in ("current_best", "v2"):
        for seed in PLAN10_NATURAL_SEEDS:
            for seat in (0, 1):
                jobs.append((
                    "plan10_exact_reference", "exact", EXACT, opponent_name,
                    OPPONENTS[opponent_name], seed, seat, "natural_plan10",
                ))
    return jobs


def main():
    locked = json.loads(OUT.read_text())["locked_hashes"]
    assert sha(EXACT) == locked["exact"]
    jobs = build_jobs()
    rows = []
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_game, job) for job in jobs]
        for future in as_completed(futures):
            rows.append(future.result())
            if len(rows) % 16 == 0 or len(rows) == len(jobs):
                print(f"completed {len(rows)}/{len(jobs)}", flush=True)
    rows.sort(key=lambda row: (
        row["opponent"], row["shop_mode"], row["seed"], row["seat"],
    ))
    payload = {
        "schema_version": 1,
        "design": "Fresh Exact controls paired to all 48 locked Plan-10 confirmation games.",
        "exact_sha256": sha(EXACT),
        "rows": rows,
    }
    REFERENCE_OUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    failures = [row for row in rows if row.get("runtime_error") or row.get("exceptions")]
    print(json.dumps({
        "games": len(rows),
        "runtime_or_agent_failures": len(failures),
        "output": str(REFERENCE_OUT),
    }, indent=2))


if __name__ == "__main__":
    main()
