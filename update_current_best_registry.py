"""Rewrite experiments/current_best.json so it states the real current state.

The v1 file is a single-pointer registry: one "best" agent plus one level of
history.  That cannot express the three roles the project actually has, which
since 2026-09-11 are different agents:

  * the highest agent verified on the leaderboard,
  * the live local research candidate,
  * the most recently packaged and the most recently submitted artifact.

This script keeps every v1 key with its v1 meaning, so ``benchmark.py``,
``analyze_top3_forensics.py``, ``finalize_top3_research.py`` and
``build_farming_v3_artifacts.py`` keep reading ``agent_path`` /
``agent_version`` / ``source_sha256`` exactly as before.  It adds a ``registry``
block for the roles a single pointer cannot carry.

It also corrects a stale promotion.  The v1 file promoted the 708-only
front-run agent on 2026-09-10 from local W/L/T.  The leaderboard snapshot taken
on 2026-09-11 (experiments/lb_calibration_report.md, CASE D) showed that agent
at 2446.5 against Terminal D's 2496.8, so the local promotion was contradicted
by later official evidence and never corrected.  ``agent_path`` therefore moves
to Terminal D, the highest agent with an actual official score.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXP = ROOT / "experiments"
REGISTRY = EXP / "current_best.json"
SOURCE_FILES = ("main.py", "policy.py", "router_parent.py", "terminal_planner.py",
                "unit_model.py", "actions.json", "settings.json")
CANDIDATE_MEMBERS = ("main.py", "policy.py", "router.py", "actions.json", "settings.json",
                     "LICENSE.txt", "NOTICE.txt")
EXECUTABLE = ("main.py", "policy.py", "router.py", "actions.json", "settings.json")

TERMINAL_D = ROOT / "agents/shop_router_0909_terminal"
STEP708 = ROOT / "agents/shop_router_0909_front_run/step708"
FULL = ROOT / "agents/shop_router_0909_front_run/full"
V233H_SAFE = ROOT / "agents/smaller_market_shock_v233h_safe"
CANDIDATE = ROOT / "agents/smaller_market_shock_v233h_non_yarn_0911"

# Public scores from experiments/lb_calibration_submissions.json, captured
# 2026-09-11T02:28:44Z, plus the later V233H Safe result.  All are dynamic
# snapshots, not final scores.
SCORES = {
    56138084: ("Terminal D", 2496.8),
    56143925: ("front-run FULL", 2461.9),
    56143730: ("front-run 708-only", 2446.5),
    56123896: ("Shop0909 Hardened", 2377.9),
    56183575: ("SmallerShockV233HSafe", 2249.4),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle_sha256(directory: Path, names) -> str:
    material = "".join(f"{name}\0{sha256(directory / name)}\n" for name in names).encode()
    return hashlib.sha256(material).hexdigest()


def archive(name: str) -> dict:
    path = ROOT / "submission" / name
    return {
        "path": f"submission/{name}",
        "exists": path.is_file(),
        "sha256": sha256(path) if path.is_file() else None,
    }


def candidate_entry() -> dict:
    lock_path = EXP / "smaller_v233h_non_yarn_0911_lock_manifest.json"
    entry = {
        "role": "the live local research candidate; no official episode has ever been played",
        "path": str(CANDIDATE.relative_to(ROOT)),
        "version": "smaller_market_shock_v233h_non_yarn_0911",
        "bundle_sha256": bundle_sha256(CANDIDATE, CANDIDATE_MEMBERS),
        "executable_bundle_sha256": bundle_sha256(CANDIDATE, EXECUTABLE),
        "parent": "agents/smaller_market_shock_v233h_safe",
        "report": "experiments/smaller_v233h_non_yarn_0911_report.md",
        "public_score": None,
        "promotion_status": "LOCAL_RESEARCH_CANDIDATE",
    }
    if lock_path.is_file():
        lock = json.loads(lock_path.read_text())
        entry["lock"] = str(lock_path.relative_to(ROOT))
        entry["lock_sha256"] = sha256(lock_path)
        entry["locked_candidate_validation_games"] = sum(
            panel.get("overall", {}).get("games", 0)
            for panel in lock["validation"].values()
            if panel.get("binds_to") == "locked_candidate"
        )
    return entry


def packaged_entry() -> dict:
    """Whichever bundle was packaged most recently, read off the packaging reports."""
    reports = {
        "smaller_market_shock_v233h_non_yarn_0911":
            EXP / "smaller_v233h_non_yarn_0911_packaging.json",
        "smaller_market_shock_v233h_safe": EXP / "smaller_v233h_safe_packaging.json",
    }
    for version, path in reports.items():
        if not path.is_file():
            continue
        payload = json.loads(path.read_text())
        deployment = payload.get("deployment", {})
        return {
            "role": "most recently packaged local artifact; packaging does not imply submission",
            "version": version,
            "archive": deployment.get("archive_path", "").replace(str(ROOT) + "/", ""),
            "archive_sha256": deployment.get("archive_sha256"),
            "packaging_report": str(path.relative_to(ROOT)),
            "all_equivalent": payload.get("all_equivalent"),
            "kaggle_submission_performed": payload.get("kaggle_submission_performed", False),
        }
    return {"role": "most recently packaged local artifact", "version": None}


def main() -> None:
    previous = json.loads(REGISTRY.read_text()) if REGISTRY.is_file() else {}
    previous_hash = sha256(REGISTRY) if REGISTRY.is_file() else None

    registry = {
        "schema_version": 2,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "schema_note": (
            "agent_path / agent_version / source_sha256 / source_bundle_sha256 keep their "
            "v1 meaning and are the only keys other scripts read: they name the single "
            "agent used as the benchmark and analysis baseline. The registry block below "
            "carries the roles a single pointer cannot express."
        ),

        # --- v1 keys, retargeted to the highest officially scored agent ---
        "agent_path": "agents/shop_router_0909_terminal/main.py",
        "agent_version": "shop_router_0909_terminal_market_smart_2pass_512",
        "source_sha256": sha256(TERMINAL_D / "main.py"),
        "source_bundle_sha256": bundle_sha256(TERMINAL_D, SOURCE_FILES),
        "promotion_status": "HIGHEST_VERIFIED_LEADERBOARD_AGENT",
        "promotion_reason": (
            "Corrects the 2026-09-10 local-W/L/T promotion of the 708-only front-run agent. "
            "The 2026-09-11 leaderboard snapshot put 708-only at 2446.5 and FULL at 2461.9, "
            "both below Terminal D at 2496.8, so the local promotion was contradicted by "
            "later official evidence. See experiments/lb_calibration_report.md (CASE D), "
            "answer 32: the Terminal-D-to-front-run direction gate failed."
        ),
        "previous_best": {
            "path": previous.get("agent_path"),
            "version": previous.get("agent_version"),
            "sha256": previous.get("source_sha256"),
            "source_bundle_sha256": previous.get("source_bundle_sha256"),
            "promotion_status": previous.get("promotion_status"),
            "superseded_reason": "local W/L/T promotion not supported by the official score",
        },
        "previous_current_best_manifest_sha256": previous_hash,

        # --- the three roles ---
        "registry": {
            "highest_verified_leaderboard_agent": {
                "role": "highest public score among our submissions with a strong local binding",
                "path": "agents/shop_router_0909_terminal/main.py",
                "version": "shop_router_0909_terminal_market_smart_2pass_512",
                "submission_id": 56138084,
                "public_score": SCORES[56138084][1],
                "score_state": "DORMANT_DYNAMIC_SNAPSHOT",
                "score_captured_at_utc": "2026-09-11T02:28:44Z",
                "source_sha256": sha256(TERMINAL_D / "main.py"),
                "source_bundle_sha256": bundle_sha256(TERMINAL_D, SOURCE_FILES),
                "submitted_archive": archive("shop_router_0909_terminal.tar.gz"),
                "binding_grade": "STRONG_INFERENCE",
                "caveat": (
                    "Kaggle does not expose the uploaded-byte SHA, so no submission has an "
                    "EXACT cryptographic binding. Every public score is a dynamic snapshot."
                ),
            },
            "current_research_candidate": candidate_entry(),
            "latest_packaged_agent": packaged_entry(),
            "latest_submitted_agent": {
                "role": "most recent upload to Kaggle",
                "path": "agents/smaller_market_shock_v233h_safe/main.py",
                "version": "smaller_market_shock_v233h_safe",
                "submission_id": 56183575,
                "public_score": SCORES[56183575][1],
                "record": "109W/26L/1T over 136 public games, GSR 0.8051",
                "bundle_sha256": bundle_sha256(V233H_SAFE, CANDIDATE_MEMBERS),
                "submitted_archive": archive("smaller_market_shock_v233h_safe.tar.gz"),
                "diagnosis": "experiments/smaller_v233h_online_submission.md",
                "note": (
                    "Scored 2249.4, below the highest verified agent. Being the newest "
                    "submission does not make it the best."
                ),
            },
        },

        "submission_score_history": [
            {"submission_id": sid, "agent": name, "public_score": score}
            for sid, (name, score) in sorted(SCORES.items(), key=lambda kv: -kv[1][1])
        ],
        "score_history_note": (
            "Snapshots from experiments/lb_calibration_submissions.json at "
            "2026-09-11T02:28:44Z, except 56183575. Scores drift as episodes accumulate and "
            "as the opponent population evolves, so values captured at different times are "
            "not directly comparable. Submission 55463623 scored 2561.0 on 2026-08-12 but "
            "has no local binding and played a much weaker population."
        ),
        "frozen_reference_agents": {
            "TerminalD": {"dir": "agents/shop_router_0909_terminal",
                          "bundle_sha256": bundle_sha256(TERMINAL_D, SOURCE_FILES)},
            "FULL": {"dir": "agents/shop_router_0909_front_run/full",
                     "bundle_sha256": bundle_sha256(FULL, SOURCE_FILES),
                     "submission_id": 56143925, "public_score": SCORES[56143925][1]},
            "STEP708": {"dir": "agents/shop_router_0909_front_run/step708",
                        "bundle_sha256": bundle_sha256(STEP708, SOURCE_FILES),
                        "submission_id": 56143730, "public_score": SCORES[56143730][1]},
        },
        "promotion_history": [
            {"date": "2026-09-09", "agent": "shop_router_0909_hardened",
             "status": "PROMOTED_RESEARCH_BEST", "submission_id": 56123896,
             "public_score": SCORES[56123896][1]},
            {"date": "2026-09-10", "agent": "shop_router_0909_terminal",
             "status": "PROMOTED_RESEARCH_BEST", "submission_id": 56138084,
             "public_score": SCORES[56138084][1]},
            {"date": "2026-09-10", "agent": "shop_router_0909_terminal_d_front_run_step708",
             "status": "PROMOTED_RESEARCH_BEST", "submission_id": 56143730,
             "public_score": SCORES[56143730][1],
             "superseded": "contradicted by the 2026-09-11 leaderboard snapshot"},
            {"date": "2026-09-12", "agent": "smaller_market_shock_v233h_safe",
             "status": "LOCAL_RESEARCH_CANDIDATE, later submitted",
             "submission_id": 56183575, "public_score": SCORES[56183575][1]},
            {"date": "2026-09-15", "agent": "smaller_market_shock_v233h_non_yarn_0911",
             "status": "LOCAL_RESEARCH_CANDIDATE", "submission_id": None,
             "public_score": None},
        ],
        "open_question": (
            "No local benchmark currently predicts leaderboard direction. "
            "experiments/lb_calibration_report.md declined to lock Benchmark V2 because "
            "source lineage is unknown for 99.05% of official matches. Treat every "
            "LOCAL_RESEARCH_CANDIDATE as unproven online."
        ),
        "kaggle_submission_made": False,
    }
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False, sort_keys=False) + "\n")
    print(REGISTRY)
    print(json.dumps({
        "agent_path": registry["agent_path"],
        "highest_verified": registry["registry"]["highest_verified_leaderboard_agent"]["public_score"],
        "research_candidate": registry["registry"]["current_research_candidate"]["version"],
        "latest_packaged": registry["registry"]["latest_packaged_agent"]["version"],
        "latest_submitted": registry["registry"]["latest_submitted_agent"]["submission_id"],
    }, indent=2))


if __name__ == "__main__":
    main()
