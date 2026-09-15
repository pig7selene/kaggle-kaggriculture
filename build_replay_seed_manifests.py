"""Extract the replay metadata the V233H screens need into small, durable manifests.

The screens only ever read four fields out of each official replay: the episode
id, the RNG seed, the team names, and the final ``unlocked_shops`` sequence.  The
replay corpora themselves live under ``/private/tmp`` and are several gigabytes,
so they are not kept.  This script distils them into two manifests that the
screens can read instead, and cross-checks every extracted value against the
experiment JSON produced by the original runs.

Run it while the ``/private/tmp`` corpora still exist.  Once the manifests are in
place the screens no longer need them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CROSS_LINEAGE_REPLAYS = Path("/private/tmp/kaggriculture_cross_lineage_20260912/replays")
ONLINE_REPLAYS = Path("/private/tmp/kaggriculture_v233h_online")
SCHEDULE_MANIFEST = ROOT / "experiments/current_top_replay_schedule_manifest.json"
SEED_MANIFEST = ROOT / "experiments/v233h_online_replay_seed_manifest.json"
SCHEDULE_CROSSCHECK = ROOT / "experiments/smaller_v233h_non_yarn_0911_fixed_current_top_schedules.json"
SEED_CROSSCHECK = ROOT / "experiments/smaller_v233h_non_yarn_0911_full_screen.json"


def _digest(value) -> str:
    material = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(material).hexdigest()


def extract_schedules() -> list[dict]:
    """Episode id, seed, teams and the full eight-shop sequence per replay."""
    rows = []
    for path in sorted(CROSS_LINEAGE_REPLAYS.glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        rows.append({
            "episode_id": int(replay["info"]["EpisodeId"]),
            "seed": int(replay["info"]["seed"]),
            "teams": list(replay["info"]["TeamNames"]),
            "shops": list(replay["steps"][-1][0]["observation"]["town"]["unlocked_shops"]),
        })
    return sorted(rows, key=lambda row: row["episode_id"])


def extract_seeds() -> list[dict]:
    """Episode id to RNG seed for the public episodes of submission 56183575."""
    rows = []
    for path in sorted(ONLINE_REPLAYS.glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        rows.append({
            "episode_id": int(replay["info"]["EpisodeId"]),
            "seed": int(replay["info"]["seed"]),
        })
    return sorted(rows, key=lambda row: row["episode_id"])


def crosscheck_schedules(rows: list[dict]) -> dict:
    """Compare against the schedules the original 90-game panel actually ran."""
    if not SCHEDULE_CROSSCHECK.is_file():
        return {"performed": False, "reason": "crosscheck artifact absent"}
    recorded = {
        int(row["episode_id"]): row
        for row in json.loads(SCHEDULE_CROSSCHECK.read_text())["source_schedules"]
    }
    mismatches = [
        {"episode_id": row["episode_id"], "field": field}
        for row in rows for field in ("seed", "shops", "teams")
        if row["episode_id"] in recorded and recorded[row["episode_id"]][field] != row[field]
    ]
    return {
        "performed": True,
        "source": str(SCHEDULE_CROSSCHECK.relative_to(ROOT)),
        "compared": len(recorded),
        "mismatches": mismatches,
        "identical": not mismatches and len(recorded) == len(rows),
    }


def crosscheck_seeds(rows: list[dict]) -> dict:
    """Compare against the seeds the original 272-game full screen actually ran."""
    if not SEED_CROSSCHECK.is_file():
        return {"performed": False, "reason": "crosscheck artifact absent"}
    recorded = {}
    for row in json.loads(SEED_CROSSCHECK.read_text())["rows"]:
        recorded.setdefault(int(row["episode_id"]), int(row["seed"]))
    extracted = {row["episode_id"]: row["seed"] for row in rows}
    mismatches = [
        {"episode_id": episode, "manifest": extracted[episode], "recorded": seed}
        for episode, seed in recorded.items()
        if episode in extracted and extracted[episode] != seed
    ]
    return {
        "performed": True,
        "source": str(SEED_CROSSCHECK.relative_to(ROOT)),
        "compared": len(recorded),
        "missing_from_manifest": sorted(set(recorded) - set(extracted)),
        "mismatches": mismatches,
        "identical": not mismatches and not set(recorded) - set(extracted),
    }


def write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"{path}  ({path.stat().st_size} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule-manifest", type=Path, default=SCHEDULE_MANIFEST)
    parser.add_argument("--seed-manifest", type=Path, default=SEED_MANIFEST)
    args = parser.parse_args()
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not CROSS_LINEAGE_REPLAYS.is_dir():
        raise SystemExit(f"source corpus missing: {CROSS_LINEAGE_REPLAYS}")
    if not ONLINE_REPLAYS.is_dir():
        raise SystemExit(f"source corpus missing: {ONLINE_REPLAYS}")

    schedules = extract_schedules()
    if len(schedules) != 15:
        raise SystemExit(f"expected 15 current-top replays, found {len(schedules)}")
    schedule_check = crosscheck_schedules(schedules)
    if not schedule_check.get("identical", False):
        raise SystemExit(f"schedule crosscheck failed: {json.dumps(schedule_check, indent=2)}")
    write(args.schedule_manifest, {
        "schema_version": 1,
        "purpose": (
            "Exact shop schedules and RNG seeds of the 15 current top-five official "
            "replays. Replaces reading the 466 MB replay corpus under /private/tmp."
        ),
        "extracted_at_utc": stamp,
        "source_corpus": str(CROSS_LINEAGE_REPLAYS),
        "source_replay_count": len(schedules),
        "crosscheck": schedule_check,
        "payload_sha256": _digest(schedules),
        "local_only": True,
        "kaggle_submission_made": False,
        "schedules": schedules,
    })

    seeds = extract_seeds()
    seed_check = crosscheck_seeds(seeds)
    if not seed_check.get("identical", False):
        raise SystemExit(f"seed crosscheck failed: {json.dumps(seed_check, indent=2)}")
    write(args.seed_manifest, {
        "schema_version": 1,
        "purpose": (
            "Episode id to RNG seed for the public episodes of submission 56183575 "
            "(SmallerShockV233HSafe). Replaces reading the 4.2 GB replay corpus under "
            "/private/tmp; the shop sequences themselves already live in "
            "experiments/smaller_v233h_online_submission.json."
        ),
        "extracted_at_utc": stamp,
        "source_corpus": str(ONLINE_REPLAYS),
        "source_replay_count": len(seeds),
        "submission_id": 56183575,
        "crosscheck": seed_check,
        "payload_sha256": _digest(seeds),
        "local_only": True,
        "kaggle_submission_made": False,
        "seeds": seeds,
    })


if __name__ == "__main__":
    main()
