"""Checkpointed V2 raw-route screen against V1-centric, replay-weighted pools."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_epic_experiments import _independent_shop_schedule, _recorded_shop_schedule
import run_super_replay_search as engine


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "agents/super_replay_v2/index.json"
MANIFEST = ROOT / "experiments/v2_top20_corpus_manifest.json"
V1_MANIFEST = ROOT / "experiments/v2_real_kaggle_replays/manifest.json"
OUTPUT = ROOT / "experiments/v2_candidate_search.json"
PARTIAL = ROOT / "experiments/v2_candidate_search.json.partial"
V1_PATH = "agents/super_replay/super_backbone_v1.py"


def _trace(path, player):
    return f"trace:{ROOT / path}:{int(player)}"


def _representative_traces(maximum=4):
    manifest = json.loads(MANIFEST.read_text())
    rows = [row for row in manifest["episodes"] if row.get("split") == "development" and row["replay_valid"]]
    rows.sort(key=lambda row: row["episode_id"])
    points = [round(i * (len(rows)-1) / (maximum-1)) for i in range(maximum)]
    output = []
    for row in [rows[i] for i in points]:
        elite = next((a for a in row["appearances"] if a["is_selected_elite_submission"]), row["appearances"][0])
        replay = json.loads((ROOT / row["replay_path"]).read_text())
        output.append({"name": f"top20_{row['episode_id']}", "path": row["replay_path"], "player": elite["seat"], "seed": row["seed"], "schedule": _recorded_shop_schedule(replay)})
    return output


def _real_v1_pressure_traces(maximum=4):
    manifest = json.loads(V1_MANIFEST.read_text())
    candidates = []
    for row in manifest["episodes"]:
        if not row["valid"]: continue
        seat = int(row["seat"]); money = row["final_money"]
        candidates.append((money[1-seat] - money[seat], row))
    candidates.sort(reverse=True, key=lambda pair: pair[0])
    output = []
    for _, row in candidates[:maximum]:
        replay = json.loads((ROOT / row["replay_path"]).read_text())
        output.append({"name": f"v1_loss_{row['episode_id']}", "path": row["replay_path"], "player": 1-int(row["seat"]), "seed": row["seed"], "schedule": _recorded_shop_schedule(replay)})
    return output


def jobs(candidates, mode):
    output = []
    traces = _real_v1_pressure_traces(2 if mode == "cheap" else 4) + _representative_traces(2 if mode == "cheap" else 4)
    rng_seeds = range(993100, 993102) if mode == "cheap" else range(993200, 993204)
    for name, path in candidates.items():
        for seed in rng_seeds:
            for seat in (0, 1):
                output.append((f"{mode}|{name}|v1f|{seed}|{seat}", path, "direct_v1_fixed", "V1", V1_PATH, seed, seat, _independent_shop_schedule(seed), {}))
                output.append((f"{mode}|{name}|v1n|{seed}|{seat}", path, "direct_v1_natural", "V1", V1_PATH, seed, seat, None, {}))
        for trace in traces:
            for seat in (0, 1):
                output.append((f"{mode}|{name}|{trace['name']}|{seat}", path, "recent_replay_trace", trace["name"], _trace(trace["path"], trace["player"]), trace["seed"], seat, trace["schedule"], {}))
    return output, traces


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--mode", choices=("cheap", "serious"), default="cheap")
    parser.add_argument("--names", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--partial", default="")
    args = parser.parse_args()
    index = json.loads(INDEX.read_text())
    if args.names:
        selected = set(args.names.split(",")); index = {name: path for name, path in index.items() if name in selected}
    run_jobs, traces = jobs(index, args.mode)
    engine.PARTIAL = Path(args.partial).resolve() if args.partial else PARTIAL
    games = engine._run_jobs(run_jobs, args.workers)
    payload = {
        "schema_version": 1, "mode": args.mode,
        "design": "V1-primary paired fixed/natural RNG plus recent V1-loss and current Top20 replay traces; both seats",
        "candidates": index, "trace_pool": traces, "jobs_expected": len(run_jobs),
        "games": games, "summary": engine._summaries(games),
    }
    target = Path(args.output).resolve() if args.output else OUTPUT
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(target)
    for path, row in sorted(payload["summary"].items(), key=lambda pair: pair[1]["average_advantage"], reverse=True):
        print(path, row["games"], row["wins"], row["losses"], round(row["average_money"],1), round(row["average_advantage"],1), round(row["p10"],1), round(row["p5"],1), row["livestock_losses"])


if __name__ == "__main__":
    main()
