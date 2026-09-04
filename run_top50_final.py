"""Locked final-unseen validation for the Top-50 distilled finalist."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from run_epic_experiments import _independent_shop_schedule, _recorded_shop_schedule
import run_super_replay_search as engine
from run_top50_parent_league import _paired


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / "experiments/top50_finalist_lock.json"
UNSEEN = ROOT / "experiments/top50_unseen_manifest.json"
OUTPUT = ROOT / "experiments/top50_final_validation.json"
BASELINE = "agents/super_replay_v2/super_backbone_v2.py"
FINALIST = "agents/top50_distilled/top50_observable_portfolio.py"
LEGACY = {
    "K3": "agents/v27_replay_weed_guard.py",
    "V1": "agents/super_replay/super_backbone_v1.py",
    "R3": "agents/leaderboard_r3_cow6_capital.py",
    "lifecycle": "agents/lifecycle_lc_combined.py",
    "adaptive_phased": "agents/adaptive_c_phased.py",
    "opponent_aware": "agents/opponent_o5_full.py",
}


def _sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _trace(path, player):
    return f"trace:{ROOT / path}:{int(player)}"


def _jobs():
    lock = json.loads(LOCK.read_text())
    if lock["finalist"]["sha256"] != _sha(FINALIST):
        raise SystemExit("locked finalist changed")
    if lock["baseline"]["sha256"] != _sha(BASELINE):
        raise SystemExit("locked baseline changed")
    conditions = []
    unseen = json.loads(UNSEEN.read_text())
    for row in unseen["episodes"]:
        replay = json.loads((ROOT / row["replay_path"]).read_text())
        for seat in (0, 1):
            conditions.append((
                f"unseen|{row['family_id']}|{row['episode_id']}|{seat}", "unseen_top50_family", f"{row['family_id']}_{row['episode_id']}",
                _trace(row["replay_path"], row["player"]), row["seed"], seat, _recorded_shop_schedule(replay),
            ))
    for seed in range(1109000, 1109016):
        for seat in (0, 1):
            conditions.append((f"v2f|{seed}|{seat}", "final_direct_v2_fixed", "V2", BASELINE, seed, seat, _independent_shop_schedule(seed)))
            conditions.append((f"v2n|{seed}|{seat}", "final_direct_v2_natural", "V2", BASELINE, seed, seat, None))
    for opponent, spec in LEGACY.items():
        for seed in range(1109200, 1109202):
            for seat in (0, 1):
                conditions.append((f"legacy|{opponent}|{seed}|{seat}", "legacy_and_adaptive", opponent, spec, seed, seat, _independent_shop_schedule(seed)))
    jobs = []
    for name, path in (("V2_baseline", BASELINE), ("top50_observable_portfolio", FINALIST)):
        for condition, group, opponent, spec, seed, seat, schedule in conditions:
            jobs.append((f"final|{name}|{condition}", path, group, opponent, spec, seed, seat, schedule, {}))
    return jobs, conditions


def main():
    jobs, conditions = _jobs()
    engine.PARTIAL = OUTPUT.with_suffix(OUTPUT.suffix + ".partial")
    games = engine._run_jobs(jobs, 8)
    payload = {
        "schema_version": 1, "split": "post-lock unused family episodes + untouched fixed/natural seeds + legacy/adaptive opponents",
        "finalist_lock_sha256": hashlib.sha256(LOCK.read_bytes()).hexdigest(),
        "conditions": len(conditions), "games": games, "summary": engine._summaries(games),
        "paired_vs_v2": _paired(games, BASELINE),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(OUTPUT)
    for path, paired in payload["paired_vs_v2"].items():
        row = payload["summary"][path]
        print(path, row["games"], row["wins"], row["losses"], round(row["average_money"], 1), round(row["average_advantage"], 1), round(paired["paired_own_money_delta_mean"], 1), round(paired["paired_own_money_delta_p10"], 1), row["actual_livestock_escapes"], row["meaningful_stranding_games"], row["runtime_failures"], row["semantic_failures"])


if __name__ == "__main__":
    main()
