"""Build a re-downloadable manifest of the V233H Safe online replay corpus.

The 4.2 GB replay corpus at /private/tmp/kaggriculture_v233h_online (submission
56183575) is outside the repository and unprotected: the same macOS /private/tmp
reaping that already destroyed v27_exact/, lb_gap_opponents/, and 7
current_meta_agents entries could take it too. This script does not copy the
replay files themselves (they stay out of the repo, per instruction) -- it
records, per episode, exactly what is needed to re-download and verify the
same batch later from Kaggle: `kaggle competitions replay <episode_id>` for
each id, then compare the downloaded file's SHA-256 against this manifest.

Named with 'manifest' so the repository's existing
`!experiments/*manifest*.json` .gitignore exception keeps it tracked.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_CORPUS = Path("/private/tmp/kaggriculture_v233h_online")
OUTPUT = ROOT / "experiments" / "smaller_v233h_safe_online_replay_manifest.json"
SUBMISSION_ID = 56183575
TEAM = "pig7selene"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entry(path: Path) -> dict:
    raw = path.read_bytes()
    replay = json.loads(raw)
    file_sha256 = hashlib.sha256(raw).hexdigest()
    teams = list(replay["info"]["TeamNames"])
    episode_id = int(replay["info"].get("EpisodeId") or path.stem.split("-")[1])
    row = {
        "episode_id": episode_id,
        "replay_filename": path.name,
        "sha256": file_sha256,
        "seed": replay["info"].get("seed"),
        "team_names": teams,
    }
    if TEAM not in teams or teams[0] == teams[1]:
        row["valid_baseline_episode"] = False
        row["skip_reason"] = (
            "team not present" if TEAM not in teams else "mirror self-play (both seats same team)"
        )
        return row

    seat = teams.index(TEAM)
    opponent = 1 - seat
    last_step = len(replay["steps"]) - 1
    final_states = replay["steps"][-1]
    own_money = float(final_states[seat]["reward"])
    opponent_money = float(final_states[opponent]["reward"])
    shops = list(replay["steps"][last_step][seat]["observation"]["town"]["unlocked_shops"])
    row.update({
        "valid_baseline_episode": True,
        "seat": seat,
        "opponent": teams[opponent],
        "first_two_shops": shops[:2],
        "own_money": own_money,
        "opponent_money": opponent_money,
        "margin": own_money - opponent_money,
        "outcome": (
            "win" if own_money > opponent_money
            else "loss" if own_money < opponent_money
            else "tie"
        ),
        "steps_recorded": last_step,
        "complete": last_step == 719,
    })
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    paths = sorted(args.corpus.glob("episode-*-replay.json"))
    if not paths:
        raise RuntimeError(f"no episode-*-replay.json files found under {args.corpus}")

    rows = [entry(path) for path in paths]
    rows.sort(key=lambda row: row["episode_id"])
    valid = [row for row in rows if row["valid_baseline_episode"]]
    outcomes = Counter(row["outcome"] for row in valid)

    manifest = {
        "schema_version": 1,
        "purpose": (
            "Per-episode identity and checksum for the public replay corpus of "
            "V233H Safe submission 56183575, so the same baseline batch can be "
            "re-downloaded via `kaggle competitions replay <episode_id>` and "
            "verified by SHA-256 if /private/tmp/kaggriculture_v233h_online is lost."
        ),
        "submission_id": SUBMISSION_ID,
        "team": TEAM,
        "source_corpus": str(args.corpus),
        "source_replay_file_count": len(paths),
        "valid_baseline_episode_count": len(valid),
        "skipped_file_count": len(paths) - len(valid),
        "valid_episode_outcomes": {
            "wins": outcomes["win"], "losses": outcomes["loss"], "ties": outcomes["tie"],
        },
        "crosscheck_against_online_submission_report": {
            "source": "experiments/smaller_v233h_online_submission.md",
            "reported": "109W/26L/1T over 136 public games, GSR 0.8051",
            "matches": (len(valid), outcomes["win"], outcomes["loss"], outcomes["tie"])
            == (136, 109, 26, 1),
        },
        "redownload_instructions": [
            "kaggle competitions episodes 56183575",
            "kaggle competitions replay <episode_id> -p <dest-dir>   # for each episode_id below",
            "verify: sha256(<dest-dir>/episode-<episode_id>-replay.json) == this manifest's "
            "'sha256' field for that episode_id",
        ],
        "kaggle_submission_made": False,
        "local_only": True,
        "episodes": rows,
    }
    args.output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(args.output)
    print(json.dumps({
        "source_replay_file_count": len(paths),
        "valid_baseline_episode_count": len(valid),
        "outcomes": dict(outcomes),
        "crosscheck_matches": manifest["crosscheck_against_online_submission_report"]["matches"],
    }, indent=2))


if __name__ == "__main__":
    main()
