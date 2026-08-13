"""Rank-held-out selection and final confirmation for super-replay finalists."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_epic_experiments import _independent_shop_schedule, _recorded_shop_schedule
from run_super_replay_search import ROOT, K3, _run_jobs, _summaries, _trace


STABILITY = ROOT / "experiments/super_replay_route_stability.json"
UNSEEN = ROOT / "experiments/super_replay_unseen_manifest.json"
OUTPUT_SELECTION = ROOT / "experiments/super_replay_selection_results.json"
OUTPUT_FINAL = ROOT / "experiments/super_replay_final_validation.json"

FINALISTS = {
    "K3": K3,
    "family02": "agents/super_replay/super_family_02_medoid.py",
    "raw_ricardo": "agents/super_replay/super_raw_55459817.py",
    "raw_hamed": "agents/super_replay/super_raw_55455766.py",
    "splice_nikita_ricardo": "agents/super_replay/super_splice_007_p1.py",
}


def _trace_pool(rank_lo, rank_hi, maximum):
    stability = json.loads(STABILITY.read_text())
    selected = [row for row in stability["submissions"] if rank_lo <= row["rank"] <= rank_hi]
    selected.sort(key=lambda row: row["rank"])
    if len(selected) > maximum:
        points = [round(index * (len(selected) - 1) / (maximum - 1)) for index in range(maximum)]
        selected = [selected[index] for index in points]
    cache = json.loads((ROOT / "experiments/super_replay_analysis_cache.json.partial").read_text())
    appearances = cache["appearances"]
    output = []
    for row in selected:
        appearance = next(value for value in appearances if value["submission_id"] == row["submission_id"] and value["episode_id"] == row["representative_episode"])
        replay = json.loads((ROOT / appearance["replay_path"]).read_text())
        output.append({
            "name": f"rank{row['rank']}_{row['submission_id']}", "rank": row["rank"],
            "path": appearance["replay_path"], "player": appearance["player"],
            "seed": appearance["seed"], "schedule": _recorded_shop_schedule(replay),
        })
    return output


def _unseen_trace_pool():
    """Load replays collected only after the finalist set was locked."""
    manifest = json.loads(UNSEEN.read_text())
    output = []
    for row in manifest["episodes"]:
        replay = json.loads((ROOT / row["replay_path"]).read_text())
        output.append({
            "name": f"unseen_rank{row['rank']}_{row['submission_id']}_{row['episode_id']}",
            "rank": row["rank"], "path": row["replay_path"], "player": row["player"],
            "seed": row["seed"], "schedule": _recorded_shop_schedule(replay),
        })
    return output


def _jobs(candidates, mode):
    jobs = []
    if mode == "selection":
        traces = _trace_pool(71, 85, 10)
        seeds = range(996200, 996204)
    else:
        traces = _unseen_trace_pool()
        seeds = range(996800, 996816)
    for name, path in candidates.items():
        for trace in traces:
            for seat in (0, 1):
                jobs.append((f"{mode}|{name}|{trace['name']}|{seat}", path, f"{mode}_elite", trace["name"], _trace(trace["path"], trace["player"]), trace["seed"], seat, trace["schedule"], {}))
        for seed in seeds:
            for seat in (0, 1):
                jobs.append((f"{mode}|{name}|k3f|{seed}|{seat}", path, f"{mode}_k3_fixed", "K3", K3, seed, seat, _independent_shop_schedule(seed), {}))
                jobs.append((f"{mode}|{name}|k3n|{seed}|{seat}", path, f"{mode}_k3_natural", "K3", K3, seed, seat, None, {}))
    return jobs, traces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("selection", "final"), required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--candidates", default="")
    args = parser.parse_args()
    candidates = FINALISTS
    if args.candidates:
        chosen = {value for value in args.candidates.split(",") if value}
        candidates = {key: value for key, value in FINALISTS.items() if key in chosen}
    output = OUTPUT_SELECTION if args.mode == "selection" else OUTPUT_FINAL
    partial = output.with_suffix(output.suffix + ".partial")
    import run_super_replay_search as search
    search.PARTIAL = partial
    jobs, traces = _jobs(candidates, args.mode)
    games = _run_jobs(jobs, args.workers)
    payload = {
        "schema_version": 1, "mode": args.mode,
        "split": "rank 71-85 selection" if args.mode == "selection" else "post-lock newly downloaded rank 86-100 replay episodes + untouched RNG seeds",
        "trace_pool": traces, "candidates": candidates, "games": games, "summary": _summaries(games),
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(output)
    for path, row in sorted(payload["summary"].items(), key=lambda value: value[1]["average_advantage"], reverse=True):
        print(path, row["games"], row["wins"], row["losses"], round(row["average_money"], 1), round(row["average_advantage"], 1), round(row["p10"], 1), round(row["route_fidelity"], 5))


if __name__ == "__main__":
    main()
