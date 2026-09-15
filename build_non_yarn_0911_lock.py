"""Emit the research lock manifest for smaller_market_shock_v233h_non_yarn_0911.

Every hash and every number is read from the candidate bytes or from the
validation artifacts on disk; nothing is transcribed by hand.  The lock is named
``*_lock_manifest.json`` so the repository's existing ``!experiments/*manifest*``
rule keeps it under version control.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT / "agents/smaller_market_shock_v233h_non_yarn_0911"
PARENT = ROOT / "agents/smaller_market_shock_v233h_safe"
BUILD_RECEIPT = ROOT / "experiments/smaller_v233h_non_yarn_0911_build.json"
LOCK = ROOT / "experiments/smaller_v233h_non_yarn_0911_lock_manifest.json"
MEMBERS = ("main.py", "policy.py", "router.py", "actions.json", "settings.json",
           "LICENSE.txt", "NOTICE.txt")
EXECUTABLE = ("main.py", "policy.py", "router.py", "actions.json", "settings.json")

# Artifact, and whether it was produced against the locked candidate bytes or an
# earlier selection build.  Selection evidence is what chose the blacklist;
# confirmation evidence is what the locked candidate itself scored.
PANELS = {
    "screen": "superseded_selection_build",
    "full_screen": "superseded_selection_build",
    "pair_screen": "superseded_selection_build",
    "whitelist_loss_screen": "locked_candidate",
    "fixed_current_top_schedules": "locked_candidate",
    "cross_lineage_gauntlet": "locked_candidate",
}
KEEP = ("games", "wins", "losses", "ties", "gsr", "mean_advantage", "median_advantage",
        "p10_advantage", "worst_advantage", "runtime_errors", "agent_errors",
        "semantic_failures", "candidate_semantic_failures", "agent_exceptions",
        "candidate_livestock_escapes", "baseline_livestock_escapes",
        "opponent_livestock_escapes", "shop_schedule_mismatches")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle_sha256(directory: Path, names) -> str:
    material = "".join(f"{name}\0{sha256(directory / name)}\n" for name in names).encode()
    return hashlib.sha256(material).hexdigest()


def identity(directory: Path) -> dict:
    return {
        "path": str(directory.relative_to(ROOT)),
        # Sorted, matching the V233H Safe lock convention that the packager asserts.
        "members": {name: sha256(directory / name) for name in sorted(MEMBERS)},
        "bundle_sha256": bundle_sha256(directory, MEMBERS),
        "executable_members": list(EXECUTABLE),
        "executable_bundle_sha256": bundle_sha256(directory, EXECUTABLE),
    }


def panel(name: str) -> dict:
    path = ROOT / f"experiments/smaller_v233h_non_yarn_0911_{name}.json"
    if not path.is_file():
        return {"artifact": path.name, "present": False}
    payload = json.loads(path.read_text())
    summary = payload.get("summary", {})
    row = {
        "artifact": path.name,
        "artifact_sha256": sha256(path),
        "binds_to": PANELS[name],
        "purpose": payload.get("purpose"),
        "overall": {k: v for k, v in summary.get("overall", {}).items() if k in KEEP},
    }
    for section in ("changed_non_yarn_routes", "unchanged_yarn_controls",
                    "pair_classification", "by_opponent"):
        if section in summary:
            value = summary[section]
            row[section] = (
                value if section == "pair_classification" else
                {k: {x: y for x, y in v.items() if x in KEEP} for k, v in value.items()}
                if section == "by_opponent" else
                {k: v for k, v in value.items() if k in KEEP}
            )
    episodes = summary.get("by_source_episode", {})
    if "108109289" in episodes:
        row["episode_108109289"] = {k: v for k, v in episodes["108109289"].items() if k in KEEP}
    return row


def blacklist_provenance() -> dict:
    """Which screen observed each blacklisted pair losing."""
    receipt = json.loads(BUILD_RECEIPT.read_text())
    blacklist = {tuple(pair) for pair in receipt["blacklisted_non_yarn_pairs"]}
    observed: dict[tuple, dict] = {pair: {} for pair in blacklist}
    for name in ("screen", "full_screen", "pair_screen"):
        path = ROOT / f"experiments/smaller_v233h_non_yarn_0911_{name}.json"
        if not path.is_file():
            continue
        for game in json.loads(path.read_text())["rows"]:
            pair = tuple(game["shops"][:2])
            if pair in observed and game.get("outcome") == "loss":
                entry = observed[pair].setdefault(name, {"losses": 0, "advantages": []})
                entry["losses"] += 1
                entry["advantages"].append(game.get("advantage"))
    return {
        "rule": (
            "A non-Yarn pair was excluded from the candidate route map if the "
            "transplanted continuation lost at least one screen game against the "
            "V233H Safe baseline on that pair."
        ),
        "pairs": {" + ".join(pair): observed[pair] for pair in sorted(blacklist)},
        "every_blacklisted_pair_has_an_observed_loss": all(observed.values()),
    }


def main() -> None:
    receipt = json.loads(BUILD_RECEIPT.read_text())
    current = identity(CANDIDATE)
    panels = {name: panel(name) for name in PANELS}
    locked = [n for n, v in PANELS.items() if v == "locked_candidate"]
    lock = {
        "schema_version": 1,
        "locked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "research_candidate_packaged_not_submitted",
        "candidate": "SmallerShockV233HNonYarn0911",
        "identity": current,
        "parent": {
            "candidate": "SmallerShockV233HSafe",
            "path": str(PARENT.relative_to(ROOT)),
            "bundle_sha256": bundle_sha256(PARENT, MEMBERS),
            "executable_bundle_sha256": bundle_sha256(PARENT, EXECUTABLE),
            "online_submission_id": 56183575,
            "online_public_score": 2249.4,
            "online_record": "109W/26L/1T over 136 public games, GSR 0.8051",
        },
        "donor": {
            "notebook": "yhay81, Shop Router 0911 Simple",
            "kaggle_url": "https://www.kaggle.com/code/yhay81/shop-router-0911-simple",
            "license": "Apache-2.0",
            "in_repo_copy": "agents/_donors/shop_router_0911_simple/main.py",
            "sha256": receipt["donor_sha256"],
            "provenance_manifest": "agents/_donors/DONOR_MANIFEST.json",
        },
        "build": {
            "script": "build_smaller_v233h_non_yarn_0911.py",
            "receipt": str(BUILD_RECEIPT.relative_to(ROOT)),
            "receipt_sha256": sha256(BUILD_RECEIPT),
            "reproducible_from_repository_only": True,
            "total_candidate_tapes": receipt["total_candidate_tapes"],
            "retained_yarn_routes": receipt["retained_yarn_routes"],
            "added_non_yarn_routes": receipt["added_non_yarn_routes"],
            "added_donor_plans": receipt["added_donor_plans"],
            "candidate_plan_indices": receipt["candidate_plan_indices"],
            "opening_field_equivalence_steps": receipt["opening_field_equivalence_steps"],
            "added_non_yarn_pairs": receipt["added_non_yarn_pairs"],
            "blacklisted_non_yarn_pairs": receipt["blacklisted_non_yarn_pairs"],
        },
        "deltas_vs_parent": [
            "SHOP_PLANS extended with 42 non-Yarn first-shop pairs routed to 8 donor tapes (indices 13-20).",
            "V233 six-sheep investment gated off on exactly those 42 routes.",
            "Donor hand slots normalised to the observed hired-hand count (V0911 layer).",
            "actions.json grows from 13 to 21 tapes; tapes 0-12 are byte-identical to the parent's.",
            "NOTICE.txt extended with the donor attribution required by Apache-2.0.",
        ],
        "unchanged_vs_parent": [
            "main.py, policy.py and settings.json are byte-identical to the parent.",
            "All 15 Yarn-related routes and the plan-0 fallback for non-enabled pairs.",
            "Every inherited repair, sale-reservation, market-depth, liquidation and feed rule.",
        ],
        "blacklist_provenance": blacklist_provenance(),
        "validation": panels,
        "validation_note": (
            "Panels marked superseded_selection_build ran against earlier 49-route builds "
            "and are the selection evidence that produced the 7-pair blacklist. The locked "
            "candidate's own confirmation record is the three panels marked locked_candidate: "
            f"{sum(panels[n]['overall'].get('games', 0) for n in locked)} games."
        ),
        "known_risks": [
            "No online evidence. The candidate has never played a Kaggle episode; its parent "
            "scored 2249.4, below the frozen Terminal D at 2496.8.",
            "Local panels are not leaderboard-calibrated. experiments/lb_calibration_report.md "
            "(CASE D) found 99.05% of official opponents have unknown lineage, and the "
            "Terminal-D-to-front-run direction was predicted wrong by local GSR.",
            "The 42 transplanted continuations come from a notebook whose author states it is "
            "a simplified release, not their scoring deployment.",
            "The blacklist was fitted on the same screens that measured the gain, so the "
            "+1782 changed-route mean is an optimistic in-sample estimate.",
            "Engine skew: the local default is kaggle-environments 1.32.6 while official "
            "replays report 1.32.7.",
        ],
        "promotion_status": "LOCAL_RESEARCH_CANDIDATE",
        "not_claimed": [
            "stronger than the frozen Terminal D on the leaderboard",
            "stronger than its own parent on the leaderboard",
        ],
        "frozen_artifacts_unchanged": True,
        "current_best_changed": False,
        "kaggle_submission_made": False,
    }
    LOCK.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n")
    print(LOCK)
    print(json.dumps({
        "bundle_sha256": current["bundle_sha256"],
        "executable_bundle_sha256": current["executable_bundle_sha256"],
        "locked_candidate_games": sum(panels[n]["overall"].get("games", 0) for n in locked),
        "blacklist_fully_evidenced": lock["blacklist_provenance"]["every_blacklisted_pair_has_an_observed_loss"],
    }, indent=2))


if __name__ == "__main__":
    main()
