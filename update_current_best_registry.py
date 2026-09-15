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

# Re-read from `kaggle competitions submissions` on 2026-09-15. This is the
# first time the same submissions have been observed at two separate dates, and
# the readings move a long way: V233H Safe has fallen 272.9 points since it was
# recorded, and the two front-run variants over 130 each, while Terminal D and
# Hardened have not moved at all. The stationary pair are dormant; the moving
# ones kept playing. So a score recorded while a submission was still active was
# never a converged value, which puts every cross-date comparison in this file
# in doubt -- including Terminal D's 2496.8, frozen at whatever point it stopped.
OBSERVED_20260915 = {
    56138084: 2496.8,
    56123896: 2377.9,
    56143925: 2327.1,
    56143730: 2298.3,
    56177294: 2159.7,
    56250442: 2034.4,
    56183575: 1976.5,
    56177298: 1778.3,
}
CANDIDATE_SUBMISSION = 56250442          # the 0911 candidate, now COMPLETE
CANDIDATE_SCORE = 2034.4
V43_SUBMISSION = 56255914                # Ahmed V43 public baseline

# Read from experiments/submission_score_trajectory_manifest.json at
# 2026-09-15T19:27Z, 18 observations in. Both V43-based curves have plateaued:
# the last three readings of each sit within ten points. The trajectory's shape
# is a climb to a peak followed by a small settle, so a plateau reading is the
# first one in this file that can be called converged rather than a snapshot.
OBSERVED_20260915T19 = {
    56258686: 2721.4,   # V43 + room_guard + clamp_sells; peak 2730.1
    56255914: 2621.7,   # V43 unmodified; peak 2628.2
    56250442: 2026.6,   # our 0911, flat since 09-15T16
}
ROOM_CLAMP_SUBMISSION = 56258686
ROOM_CLAMP_SCORE = OBSERVED_20260915T19[56258686]
ROOM_CLAMP_ARCHIVE_SHA = "fd710687180a0260742f25bb3205f0e6dab7ea9083f74d65037491d0b95f34c4"
ROOM_CLAMP_MAIN_SHA = "9bc82ca6c2f22707f352a7f988fbfda153107d665d1f4cd328b8943f63e97647"


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
        "role": "submitted and scored; superseded as a research direction",
        "path": str(CANDIDATE.relative_to(ROOT)),
        "version": "smaller_market_shock_v233h_non_yarn_0911",
        "bundle_sha256": bundle_sha256(CANDIDATE, CANDIDATE_MEMBERS),
        "executable_bundle_sha256": bundle_sha256(CANDIDATE, EXECUTABLE),
        "parent": "agents/smaller_market_shock_v233h_safe",
        "report": "experiments/smaller_v233h_non_yarn_0911_report.md",
        "submission_id": CANDIDATE_SUBMISSION,
        "public_score": CANDIDATE_SCORE,
        "parent_public_score_same_day": OBSERVED_20260915[56183575],
        "gain_over_parent_same_day": round(CANDIDATE_SCORE - OBSERVED_20260915[56183575], 1),
        "promotion_status": "SUBMITTED_AND_SCORED",
        "verdict": (
            "The 42 non-Yarn routes are worth +57.9 against the parent read on the same "
            "day, which answers the pre-registered primary question in the affirmative "
            "and is also almost irrelevant: the whole lineage sits near 2000 while the "
            "leaderboard's fourth to fifteenth places sit between 2969 and 3034, and "
            "Ahmed V43 beat this candidate 32-0 locally."
        ),
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
                "version": "ahmed_v43_public_plus_room_guard_clamp_sells",
                "submission_id": ROOM_CLAMP_SUBMISSION,
                "public_score": ROOM_CLAMP_SCORE,
                "public_score_peak": 2730.1,
                "score_state": "ACTIVE_PLATEAU",
                "score_captured_at_utc": "2026-09-15T19:27:03Z",
                "origin": "ahmedberatozer/kaggriculture-v43-recovering-lost-harvests (Apache-2.0)",
                "ours": "derived: the public V43 chassis with two of its own disabled layers "
                        "enabled; the one-line change and its selection are ours, the agent is not",
                "change_vs_base": {"room_guard": True, "clamp_sells": True},
                "selected_by": "experiments/v43_layer_ablation.md (37/3/0, +440 mean margin)",
                "main_sha256": ROOM_CLAMP_MAIN_SHA,
                "submitted_archive": archive("v43_room_clamp.tar.gz"),
                "submitted_archive_sha256_expected": ROOM_CLAMP_ARCHIVE_SHA,
                "gain_over_unmodified_v43_same_window": round(
                    ROOM_CLAMP_SCORE - OBSERVED_20260915T19[V43_SUBMISSION], 1),
                "gain_over_terminal_d": round(ROOM_CLAMP_SCORE - SCORES[56138084][1], 1),
                "binding_grade": "STRONG_INFERENCE",
                "caveat": (
                    "Kaggle does not expose the uploaded-byte SHA, so no submission has an "
                    "EXACT cryptographic binding. Score is a plateau reading, still moving "
                    "by single digits."
                ),
            },
            "previous_highest_verified_leaderboard_agent": {
                "path": "agents/shop_router_0909_terminal/main.py",
                "version": "shop_router_0909_terminal_market_smart_2pass_512",
                "submission_id": 56138084,
                "public_score": SCORES[56138084][1],
                "score_state": "DORMANT_DYNAMIC_SNAPSHOT",
                "score_captured_at_utc": "2026-09-11T02:28:44Z",
                "source_sha256": sha256(TERMINAL_D / "main.py"),
                "source_bundle_sha256": bundle_sha256(TERMINAL_D, SOURCE_FILES),
                "submitted_archive": archive("shop_router_0909_terminal.tar.gz"),
                "superseded_on": "2026-09-15",
                "superseded_by": ROOM_CLAMP_SUBMISSION,
                "note": "Frozen at an unknown point on its curve; lost 32/0 to unmodified V43 locally.",
            },
            "current_research_candidate": candidate_entry(),
            "latest_packaged_agent": packaged_entry(),
            "latest_submitted_agent": {
                "role": "most recent upload to Kaggle",
                "version": "ahmed_v43_public_plus_room_guard_clamp_sells",
                "submission_id": ROOM_CLAMP_SUBMISSION,
                "public_score": ROOM_CLAMP_SCORE,
                "status": "COMPLETE, plateaued",
                "submitted_archive": archive("v43_room_clamp.tar.gz"),
                "note": "Same agent as highest_verified_leaderboard_agent.",
            },
            "v43_unmodified_baseline": {
                "role": "the public base, submitted unmodified so its reading attributes to it alone",
                "submission_id": V43_SUBMISSION,
                "public_score": OBSERVED_20260915T19[V43_SUBMISSION],
                "public_score_peak": 2628.2,
                "origin": "ahmedberatozer/kaggriculture-v43-recovering-lost-harvests",
                "license": "Apache-2.0",
                "ours": False,
                "submitted_archive": archive("ahmed_v43_public.tar.gz"),
                "rationale": "experiments/ahmed_v43_adoption.md",
                "predicted_before_submission": "2900-3000",
                "prediction_outcome": (
                    "wrong by roughly 300: the strongest public notebook alone reaches about "
                    "2620, so the 2969-3034 leaderboard band is not public material plus tweaks"
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
             "status": "SUBMITTED_AND_SCORED", "submission_id": CANDIDATE_SUBMISSION,
             "public_score": CANDIDATE_SCORE,
             "note": "+57.9 over its parent read the same day; the lineage sits near 2000"},
            {"date": "2026-09-15", "agent": "ahmed_v43_public_unmodified",
             "status": "BASE_CHANGED", "submission_id": V43_SUBMISSION,
             "public_score": OBSERVED_20260915T19[V43_SUBMISSION], "ours": False,
             "note": "won 64 of 64 against both of ours locally; plateaued near 2622 online"},
            {"date": "2026-09-15", "agent": "ahmed_v43_public_plus_room_guard_clamp_sells",
             "status": "PROMOTED_HIGHEST_VERIFIED", "submission_id": ROOM_CLAMP_SUBMISSION,
             "public_score": ROOM_CLAMP_SCORE,
             "note": (
                 "two of V43's nine layers enabled after a 360-game ablation; +440 local margin "
                 "predicted about +37 online, observed about +100 -- the local-to-online "
                 "conversion is more favourable than the cross-lineage V43-vs-0911 ratio implied"
             )},
        ],
        "score_drift_20260911_to_20260915": {
            "note": (
                "The same submissions read at two dates. Dormant submissions do not move; "
                "active ones fall. A score recorded while a submission was still playing "
                "was therefore not a converged value, and cross-date comparisons in the "
                "rest of this file, Terminal D's 2496.8 included, inherit that doubt."
            ),
            "rows": [
                {"submission_id": sid, "agent": SCORES[sid][0],
                 "recorded_20260911": SCORES[sid][1],
                 "observed_20260915": OBSERVED_20260915[sid],
                 "delta": round(OBSERVED_20260915[sid] - SCORES[sid][1], 1)}
                for sid in sorted(SCORES, key=lambda s: -SCORES[s][1])
                if sid in OBSERVED_20260915
            ],
        },
        "leaderboard_context_20260915": {
            "top": {"Majkel1337": 3166.7, "Artem The Farmer": 3138.8,
                    "Unknown Mother-Goose": 3093.9, "DSM": 3034.0},
            "places_4_to_15_band": [2969.7, 3034.0],
            "our_best_observed": OBSERVED_20260915[56138084],
            "gap_to_band": round(2969.7 - OBSERVED_20260915[56138084], 1),
        },
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
