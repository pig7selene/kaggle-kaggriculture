"""Selection and locked final-unseen validation for Super Backbone V2."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from run_epic_experiments import _independent_shop_schedule, _recorded_shop_schedule
import run_super_replay_search as engine


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "experiments/v2_top20_corpus_manifest.json"
OUTPUT_SELECTION = ROOT / "experiments/v2_selection_validation.json"
OUTPUT_FINAL = ROOT / "experiments/v2_final_validation.json"
LOCK = ROOT / "experiments/v2_finalists_lock.json"
V1 = "agents/super_replay/super_backbone_v1.py"

SELECTION_CANDIDATES = {
    "V1": V1,
    "jalkarna_complete": "agents/super_replay_v2/v2_raw_55463387.py",
    "nazmus_complete": "agents/super_replay_v2/v2_raw_55445174.py",
    "jalkarna_tail": "agents/super_replay_v2/v2_splice_jalkarna_p2_tail.py",
}
FINALISTS = {
    "V1": V1,
    "jalkarna_complete": "agents/super_replay_v2/v2_raw_55463387.py",
}


def _sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _trace(path, player):
    return f"trace:{ROOT / path}:{int(player)}"


def _eligible_traces(split, maximum=None):
    manifest = json.loads(MANIFEST.read_text())
    excluded = {92432072, 92460802, 92476747, 92510063, 92468241, 92481357}
    rows = [row for row in manifest["episodes"] if row.get("split") == split and row["replay_valid"]]
    candidates = []
    for row in rows:
        elite = [a for a in row["appearances"] if a["is_selected_elite_submission"]]
        if not elite:
            continue
        elite.sort(key=lambda a: (a["leaderboard_rank"] or 999, a["seat"]))
        appearance = elite[0]
        candidates.append((appearance["leaderboard_rank"] or 999, row, appearance))
    if split == "development":
        candidates = [value for value in candidates if value[1]["episode_id"] not in excluded]
        selected = []
        seen_submissions = set()
        for _, row, appearance in sorted(candidates, key=lambda value: (value[0], value[1]["episode_id"])):
            if appearance["submission_id"] in seen_submissions:
                continue
            seen_submissions.add(appearance["submission_id"])
            selected.append((row, appearance))
            if len(selected) == maximum:
                break
    else:
        selected = [(row, appearance) for _, row, appearance in sorted(candidates, key=lambda value: (value[0], value[1]["episode_id"]))]
    output = []
    for row, appearance in selected:
        replay = json.loads((ROOT / row["replay_path"]).read_text())
        output.append({
            "name": f"rank{appearance['leaderboard_rank']}_{appearance['submission_id']}_{row['episode_id']}",
            "rank": appearance["leaderboard_rank"], "submission_id": appearance["submission_id"],
            "episode_id": row["episode_id"], "path": row["replay_path"], "player": appearance["seat"],
            "seed": row["seed"], "schedule": _recorded_shop_schedule(replay),
        })
    return output


def _jobs(candidates, mode):
    traces = _eligible_traces("development", 8) if mode == "selection" else _eligible_traces("final_holdout")
    seeds = range(993600, 993608) if mode == "selection" else range(994600, 994608)
    jobs = []
    for name, path in candidates.items():
        for trace_row in traces:
            for seat in (0, 1):
                jobs.append((f"{mode}|{name}|{trace_row['name']}|{seat}", path, f"{mode}_recent_trace", trace_row["name"], _trace(trace_row["path"], trace_row["player"]), trace_row["seed"], seat, trace_row["schedule"], {}))
        for seed in seeds:
            for seat in (0, 1):
                jobs.append((f"{mode}|{name}|v1f|{seed}|{seat}", path, f"{mode}_direct_v1_fixed", "V1", V1, seed, seat, _independent_shop_schedule(seed), {}))
                jobs.append((f"{mode}|{name}|v1n|{seed}|{seat}", path, f"{mode}_direct_v1_natural", "V1", V1, seed, seat, None, {}))
    return jobs, traces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("selection", "final"), required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.mode == "selection":
        candidates = SELECTION_CANDIDATES
        output = OUTPUT_SELECTION
    else:
        if not LOCK.exists():
            raise SystemExit("finalists must be locked after selection before final holdout is queried")
        lock = json.loads(LOCK.read_text())
        for name, path in FINALISTS.items():
            if lock["finalists"][name]["sha256"] != _sha(path):
                raise SystemExit(f"locked finalist changed: {name}")
        candidates = FINALISTS
        output = OUTPUT_FINAL
    jobs, traces = _jobs(candidates, args.mode)
    engine.PARTIAL = output.with_suffix(output.suffix + ".partial")
    games = engine._run_jobs(jobs, args.workers)
    payload = {
        "schema_version": 1, "mode": args.mode, "candidates": candidates,
        "trace_pool": traces, "jobs_expected": len(jobs), "games": games,
        "summary": engine._summaries(games),
        "split": "unseen development traces + untouched RNG" if args.mode == "selection" else "locked current-Top20 holdout episodes + untouched RNG",
    }
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.mode == "selection" and not LOCK.exists():
        LOCK.write_text(json.dumps({
            "schema_version": 1,
            "policy": "Only V1 and JALKARNA complete route may see final_holdout episodes; no tuning after lock.",
            "selection_result_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "finalists": {name: {"path": path, "sha256": _sha(path)} for name, path in FINALISTS.items()},
        }, indent=2, sort_keys=True) + "\n")
    print(output)
    for path, row in sorted(payload["summary"].items(), key=lambda pair: pair[1]["average_advantage"], reverse=True):
        print(path, row["games"], row["wins"], row["losses"], row["ties"], round(row["average_money"],1), round(row["average_advantage"],1), round(row["p10"],1), round(row["p5"],1), row["livestock_losses"])


if __name__ == "__main__":
    main()
