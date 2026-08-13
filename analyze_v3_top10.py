"""Development-only Top-10 reconstruction, stability, routes, and divergences."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import statistics

import analyze_super_replays as base
import collect_super_replays as collector
from collect_v3_replays import _apply_splits


ROOT = Path(__file__).resolve().parent
COLLECTION = ROOT / "experiments/v3_top10_corpus_manifest.json.partial"
PUBLIC_MANIFEST = ROOT / "experiments/v3_top10_corpus_manifest.json"
DEV_MANIFEST = ROOT / "experiments/v3_top10_development_manifest.json"
REPLAYS = ROOT / "experiments/v3_top10_corpus/replays"
STABILITY = ROOT / "experiments/v3_route_stability.json"
FAMILIES = ROOT / "experiments/v3_route_families.json"
WAVES = ROOT / "experiments/v3_economic_waves.json"
CONFIDENCE = ROOT / "experiments/v3_action_confidence.json"
ROUTE_BANK = ROOT / "experiments/v3_route_bank.json"
EXECUTOR = ROOT / "experiments/v3_route_executor.json"
DIVERGENCES = ROOT / "experiments/v3_within_submission_divergences.json"
FINANCIAL = ROOT / "experiments/v3_financial_reconstruction.json"


def _sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _prepare_manifests():
    raw = _apply_splits(json.loads(COLLECTION.read_text()))
    dev_ids = set(raw["splits"]["development_episode_ids"])

    # The public corpus manifest records the frozen split and collection
    # status without inspecting protected actions during development.
    public = deepcopy(raw)
    public["episodes"] = [
        {
            "episode_id": int(meta["id"]),
            "split": next(
                (s for s in ("final_holdout", "selection", "development")
                 if int(meta["id"]) in set(raw["splits"][f"{s}_episode_ids"])),
                None,
            ),
            "create_time": meta.get("createTime"),
            "end_time": meta.get("endTime"),
            "agents": meta.get("agents", []),
            "downloaded": (REPLAYS / f"episode-{int(meta['id'])}-replay.json").exists(),
        }
        for submission in raw["submissions"]
        for meta in submission.get("selected_episode_metadata", [])
    ]
    seen = set()
    public["episodes"] = [row for row in public["episodes"] if not (row["episode_id"] in seen or seen.add(row["episode_id"]))]
    public["corpus_summary"]["split_unique_episode_counts"] = {
        tier: len(raw["splits"][f"{tier}_episode_ids"])
        for tier in ("development", "selection", "final_holdout")
    }
    public["holdout_actions_opened_for_development"] = False
    PUBLIC_MANIFEST.write_text(json.dumps(public, indent=2, ensure_ascii=False, sort_keys=True) + "\n")

    # Financial reconstruction is performed before action mining. One replay
    # covers both selected appearances when elite agents face each other.
    audits, excluded = [], set()
    for index, eid in enumerate(sorted(dev_ids), 1):
        path = REPLAYS / f"episode-{eid}-replay.json"
        if not path.exists():
            audits.append({"episode_id": eid, "eligible": False, "reason": "missing_replay", "mismatches": []})
            excluded.add(eid)
            continue
        replay = json.loads(path.read_text())
        _, errors = base._timeline(replay, 0)
        eligible = not errors
        audits.append({
            "episode_id": eid,
            "eligible": eligible,
            "reason": None if eligible else "financial_reconstruction_mismatch",
            "mismatch_count": len(errors),
            "mismatches": errors,
            "final_money": [float(v["reward"]) for v in replay["steps"][-1]],
        })
        if not eligible:
            excluded.add(eid)
        if index % 10 == 0:
            print(f"financial audit {index}/{len(dev_ids)}", flush=True)
    FINANCIAL.write_text(json.dumps({
        "schema_version": 1,
        "development_replays": len(dev_ids),
        "eligible_replays": len(dev_ids) - len(excluded),
        "excluded_replays": len(excluded),
        "total_mismatches": sum(row.get("mismatch_count", 0) for row in audits),
        "audits": audits,
    }, indent=2, sort_keys=True) + "\n")

    dev = deepcopy(raw)
    dev["selected_episode_ids"] = sorted(dev_ids - excluded)
    for submission in dev["submissions"]:
        submission["selected_episode_metadata"] = [
            row for row in submission.get("selected_episode_metadata", [])
            if int(row["id"]) in dev_ids - excluded
        ]
        submission["selected_episode_ids"] = [int(row["id"]) for row in submission["selected_episode_metadata"]]
    collector.REPLAYS = REPLAYS
    dev = collector._finalize(dev)
    for row in dev["episodes"]:
        row["split"] = "development"
    DEV_MANIFEST.write_text(json.dumps(dev, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    return dev


def _state_features(row, step):
    anchor = row["anchors"][step]
    replay = json.loads((ROOT / row["replay_path"]).read_text())
    obs = replay["steps"][step][row["player"]]["observation"]
    other = obs["farms"][1 - row["player"]]
    opponent = base._counts(other)
    prices = obs["market"]["prices"]
    recent = {}
    for item in ("MILK", "WOOL", "STRAWBERRY", "MELON", "WHEAT"):
        older = replay["steps"][max(0, step - 24)][row["player"]]["observation"]["market"]["prices"][item]
        recent[item] = int(prices[item]) - int(older)
    return {
        "step": step,
        "bank": float(anchor.get("money", 0)),
        "land_count": len(anchor.get("quadrants", [])),
        "hand_count": int(anchor.get("hand_count", 0)),
        "animals": anchor.get("animals", {}),
        "crops": anchor.get("crops", {}),
        "productive": anchor.get("productive", 0),
        "weeds": anchor.get("weeds", 0),
        "shed": anchor.get("shed", {}),
        "seeds": anchor.get("seeds", {}),
        "market_prices": {k: prices[k] for k in ("MILK", "WOOL", "STRAWBERRY", "MELON", "WHEAT")},
        "market_price_change_24": recent,
        "opponent_crops": opponent["crops"],
        "opponent_animals": opponent["animals"],
        "opponent_productive": opponent["productive"],
    }


def _meaningful(action):
    return {
        "farmer": action["farmer"],
        "hands": action["hands"],
        "market": action["market"],
    }


def _enrich_outputs():
    cache = json.loads((ROOT / "experiments/v3_top10_analysis_cache.json.partial").read_text())
    appearances = cache["appearances"]
    grouped = defaultdict(list)
    for row in appearances:
        grouped[row["submission_id"]].append(row)

    divergence_rows = []
    for submission, rows in grouped.items():
        if len(rows) < 2:
            continue
        representative = max(rows, key=lambda left: sum(sum(a == b for a, b in zip(left["actions"], right["actions"])) for right in rows))
        for row in rows:
            if row is representative:
                continue
            step = next((i for i, (a, b) in enumerate(zip(representative["actions"], row["actions"])) if _meaningful(a) != _meaningful(b)), None)
            if step is None:
                continue
            divergence_rows.append({
                "submission_id": submission,
                "team_name": row["team_name"],
                "representative_episode": representative["episode_id"],
                "episode_id": row["episode_id"],
                "first_divergence_step": step,
                "representative_action": representative["actions"][step],
                "branch_action": row["actions"][step],
                "branch_label": _sha(row["actions"][step:min(719, step + 24)]),
                "observable_state": _state_features(row, step),
                "representative_final_money": representative["final_money"],
                "branch_final_money": row["final_money"],
                "observational_money_delta": row["final_money"] - representative["final_money"],
                "causal_status": "observational_only; requires paired counterfactual",
            })
    DIVERGENCES.write_text(json.dumps({
        "schema_version": 1,
        "records": divergence_rows,
        "submissions_with_divergence": len({row["submission_id"] for row in divergence_rows}),
        "note": "First within-version action divergence and observable pre-action state; not treated as causal branch evidence.",
    }, indent=2, ensure_ascii=False, sort_keys=True) + "\n")

    stability = json.loads(STABILITY.read_text())
    for row in stability["submissions"]:
        source_rows = grouped[row["submission_id"]]
        schedules = {}
        for name in ("first_land", "second_land", "first_animal_buy", "hands_6", "hands_8", "hands_10", "cows_4", "cows_6", "cows_8", "first_sell", "last_sell"):
            values = [r["milestones"].get(name) for r in source_rows]
            counts = Counter(str(value) for value in values)
            schedules[name] = {
                "mode": values[0] if len(set(values)) == 1 else statistics.mode(values),
                "stability": counts.most_common(1)[0][1] / len(values),
                "range": [min((v for v in values if v is not None), default=None), max((v for v in values if v is not None), default=None)],
            }
        row["schedule_stability"] = schedules
        phase_scores = row["stability"]
        row["high_resolution_classification"] = (
            "fixed" if all(v["field"] >= .97 and v["market"] >= .94 for v in phase_scores.values())
            else "fixed_bounded_repair" if all(v["field"] >= .90 for v in phase_scores.values())
            else "phase_adaptive" if min(v["field"] for v in phase_scores.values()) >= .70
            else "branch_adaptive" if min(v["field"] for v in phase_scores.values()) >= .45
            else "strongly_adaptive"
        )
    STABILITY.write_text(json.dumps(stability, indent=2, ensure_ascii=False, sort_keys=True) + "\n")

    bank = json.loads(ROUTE_BANK.read_text())
    minimal = []
    for route in bank["routes"]:
        minimal.append({key: route.get(key) for key in (
            "route_id", "family_id", "source_submission_id", "source_team", "source_episode_id",
            "source_player", "source_seed", "source_replay_path", "source_final_money",
            "consensus_actions", "expected_state", "milestones", "appearance_count",
            "average_source_money", "stability_class",
        ) if key in route})
    EXECUTOR.write_text(json.dumps({"schema_version": 1, "route_count": len(minimal), "routes": minimal}, separators=(",", ":")) + "\n")


def main():
    dev = _prepare_manifests()
    base.CORPUS_MANIFEST = DEV_MANIFEST
    base.STABILITY_OUT = STABILITY
    base.FAMILIES_OUT = FAMILIES
    base.WAVES_OUT = WAVES
    base.CONFIDENCE_OUT = CONFIDENCE
    base.ROUTE_BANK_OUT = ROUTE_BANK
    base.CACHE = ROOT / "experiments/v3_top10_analysis_cache.json.partial"
    base.main()
    _enrich_outputs()
    financial = json.loads(FINANCIAL.read_text())
    stability = json.loads(STABILITY.read_text())
    families = json.loads(FAMILIES.read_text())
    print(json.dumps({
        "development_unique_episodes": len(dev["episodes"]),
        "financial_mismatches": financial["total_mismatches"],
        "submissions": stability["submission_count"],
        "appearances": stability["unique_selected_appearances_after_action_dedup"],
        "families": families["family_count"],
        "routes": json.loads(EXECUTOR.read_text())["route_count"],
    }, indent=2))


if __name__ == "__main__":
    main()
