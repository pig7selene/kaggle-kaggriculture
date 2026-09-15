"""Build a re-downloadable manifest of the Majkel1337 56156662 replay corpus.

The corpus at /private/tmp/kaggriculture_majkel_56156662 (43 replays, 1.3 GB) is
the training, development and sealed-holdout data for the G0/G1 route
reconstruction line. It sits outside the repository, on the same /private/tmp
that has already been reaped once this week. This script records what is needed
to re-download and verify every episode rather than copying 1.3 GB into git.

Seal discipline, enforced below rather than merely documented:

The six episodes named in experiments/majkel_g1_split_lock.json are a sealed G1
holdout. For those, this script computes a SHA-256 and nothing else -- it never
parses their JSON. Hashing is what the seal itself did when it registered them
("new_holdout_downloaded_and_hash_registered_but_unopened"), so it is
seal-compatible by the seal's own precedent; parsing out shop pairs, seats or
outcomes would not be. Every computed holdout hash is checked against the value
the seal registered, so a swapped or truncated file is caught here.

Named with 'manifest' so the repository's existing !experiments/*manifest*.json
exception keeps it tracked.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_CORPUS = Path("/private/tmp/kaggriculture_majkel_56156662")
SEAL = ROOT / "experiments" / "majkel_g1_split_lock.json"
# Three declared development episodes live outside the Majkel corpus directory,
# under the current-meta corpus, so the split manifest's recorded paths are
# walked too. Without this the manifest would cover 37 of the 40 declared.
G0_SPLIT = ROOT / "experiments" / "majkel_56156662_split_manifest.json"
OUTPUT = ROOT / "experiments" / "majkel_56156662_corpus_manifest.json"
SUBMISSION_ID = 56156662
TEAM = "Majkel1337"
SUBSETS = ("pool", "g1_development_extra", "g1_holdout")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def episode_id(path: Path) -> int:
    return int(path.stem.split("-")[1])


def sealed_entry(path: Path, registered: dict) -> dict:
    """Hash only. This file's contents are never read as JSON."""
    eid = episode_id(path)
    digest = sha256(path)
    expected = registered.get(str(eid))
    return {
        "episode_id": eid,
        "replay_filename": path.name,
        "sha256": digest,
        "subset": "g1_holdout",
        "sealed": True,
        "contents_parsed": False,
        "matches_seal_registered_hash": None if expected is None else digest == expected,
    }


def open_entry(path: Path, subset: str) -> dict:
    """Full metadata. Only ever called for episodes outside the sealed holdout."""
    raw = path.read_bytes()
    replay = json.loads(raw)
    teams = list(replay["info"]["TeamNames"])
    row = {
        "episode_id": episode_id(path),
        "replay_filename": path.name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "subset": subset,
        "sealed": False,
        "contents_parsed": True,
        "seed": replay["info"].get("seed"),
        "team_names": teams,
    }
    if TEAM in teams and teams[0] != teams[1]:
        seat = teams.index(TEAM)
        other = 1 - seat
        last = len(replay["steps"]) - 1
        final = replay["steps"][-1]
        own, opp = float(final[seat]["reward"]), float(final[other]["reward"])
        row.update({
            "target_seat": seat,
            "opponent": teams[other],
            "first_two_shops": list(
                replay["steps"][last][seat]["observation"]["town"]["unlocked_shops"]
            )[:2],
            "target_money": own,
            "opponent_money": opp,
            "margin": own - opp,
            "outcome": "win" if own > opp else "loss" if own < opp else "tie",
            "steps_recorded": last,
            "complete": last == 719,
        })
    else:
        row["target_present"] = False
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    seal = json.loads(SEAL.read_text())
    sealed_ids = set(seal["sealed_holdout_episode_ids"])
    registered = seal["sealed_holdout_replay_hashes"]

    rows = []
    for subset in SUBSETS:
        for path in sorted((args.corpus / subset).glob("episode-*-replay.json")):
            eid = episode_id(path)
            if eid in sealed_ids:
                if subset != "g1_holdout":
                    raise RuntimeError(
                        f"sealed episode {eid} found outside g1_holdout, in {subset}"
                    )
                rows.append(sealed_entry(path, registered))
            else:
                if subset == "g1_holdout":
                    raise RuntimeError(
                        f"unsealed episode {eid} found inside g1_holdout"
                    )
                rows.append(open_entry(path, subset))

    # Declared development episodes stored outside the corpus directory.
    captured = {row["episode_id"] for row in rows}
    for group in ("training", "holdout"):
        for record in json.loads(G0_SPLIT.read_text())[group]:
            path = Path(record["replay_path"])
            eid = int(record["episode_id"])
            if eid in captured or eid in sealed_ids or not path.is_file():
                continue
            rows.append(open_entry(path, f"external:{path.parent.parent.name}"))
            rows[-1]["source_path"] = str(path)
            rows[-1]["g0_split_group"] = group
            captured.add(eid)
    rows.sort(key=lambda row: row["episode_id"])

    sealed_rows = [row for row in rows if row["sealed"]]
    open_rows = [row for row in rows if not row["sealed"]]
    on_disk_sealed = {row["episode_id"] for row in sealed_rows}
    declared_dev = set(seal["development_episode_ids"]) | set(
        seal["additional_development_episode_ids_selected_before_download"]
    )
    outcomes = Counter(row["outcome"] for row in open_rows if "outcome" in row)

    manifest = {
        "schema_version": 1,
        "purpose": (
            "Per-episode identity and checksum for the Majkel1337 submission "
            "56156662 replay corpus (G0/G1 route reconstruction data), so the "
            "corpus can be re-downloaded and verified if "
            "/private/tmp/kaggriculture_majkel_56156662 is lost."
        ),
        "submission_id": SUBMISSION_ID,
        "team": TEAM,
        "source_corpus": str(args.corpus),
        "seal": {
            "file": str(SEAL.relative_to(ROOT)),
            "sha256": sha256(SEAL),
            "status": seal["status"],
            "holdout_actions_read": seal["holdout_actions_read"],
        },
        "counts": {
            "total_replays": len(rows),
            "sealed_holdout": len(sealed_rows),
            "open_development": len(open_rows),
            "by_subset": dict(Counter(row["subset"] for row in rows)),
        },
        "seal_integrity": {
            "sealed_ids_declared": sorted(sealed_ids),
            "sealed_ids_on_disk": sorted(on_disk_sealed),
            "all_declared_present": on_disk_sealed == sealed_ids,
            "all_hashes_match_seal": all(
                row["matches_seal_registered_hash"] for row in sealed_rows
            ),
            "holdout_contents_parsed_by_this_script": False,
        },
        "development_coverage": {
            "declared_development_ids": len(declared_dev),
            "open_replays_on_disk": len(open_rows),
            "declared_but_absent": sorted(
                declared_dev - {row["episode_id"] for row in open_rows}
            ),
            "on_disk_but_undeclared": sorted(
                {row["episode_id"] for row in open_rows} - declared_dev
            ),
        },
        "open_development_outcomes": {
            "wins": outcomes["win"], "losses": outcomes["loss"], "ties": outcomes["tie"],
        },
        "redownload_instructions": [
            "kaggle competitions episodes 56156662",
            "kaggle competitions replay <episode_id> -p <dest-dir>/<subset>",
            "verify: sha256 of each file equals this manifest's 'sha256' for that episode_id",
            "the six sealed episodes must be restored into a g1_holdout/ directory and "
            "left unparsed; their hashes are independently registered in "
            "experiments/majkel_g1_split_lock.json",
        ],
        "local_only": True,
        "episodes": rows,
    }
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(args.output)
    print(json.dumps({
        "counts": manifest["counts"],
        "seal_integrity": {
            k: v for k, v in manifest["seal_integrity"].items()
            if k not in ("sealed_ids_declared", "sealed_ids_on_disk")
        },
        "development_coverage": manifest["development_coverage"],
    }, indent=2))


if __name__ == "__main__":
    main()
