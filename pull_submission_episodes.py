"""Download a submission's online episodes and index them.

Kaggle's episode service lists a submission's episodes without authentication
(`competitions.EpisodeService/ListEpisodes`), and each replay is served at
https://www.kaggle.com/competitions/episodes/<id>/replay.json (~32 MB). Replays
go to /private/tmp (never into the repository); the manifest with per-episode
metadata and file hashes goes to experiments/. Idempotent: existing files are
kept, the manifest is rebuilt from the current listing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
LIST_URL = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
REPLAY_URL = "https://www.kaggle.com/competitions/episodes/{id}/replay.json"
OUT_ROOT = Path("/private/tmp/kaggriculture_online")


def list_episodes(submission: int) -> dict:
    req = urllib.request.Request(LIST_URL, data=json.dumps({"submissionId": submission}).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission", type=int, required=True)
    parser.add_argument("--max", type=int, default=400)
    args = parser.parse_args()
    out = OUT_ROOT / str(args.submission)
    out.mkdir(parents=True, exist_ok=True)
    listing = list_episodes(args.submission)
    teams = {t["id"]: t.get("teamName") for t in listing.get("teams", [])}
    episodes = [e for e in listing.get("episodes", []) if e.get("state") == "COMPLETED"]
    print(f"submission {args.submission}: {len(episodes)} completed episodes listed", flush=True)
    rows = []
    for e in sorted(episodes, key=lambda e: e["createTime"])[: args.max]:
        path = out / f"episode-{e['id']}-replay.json"
        if not path.is_file() or path.stat().st_size < 1000:
            for attempt in range(3):
                try:
                    urllib.request.urlretrieve(REPLAY_URL.format(id=e["id"]), path)
                    break
                except Exception as exc:
                    time.sleep(2 + attempt * 3)
                    if attempt == 2:
                        print(f"  failed {e['id']}: {exc!r}", flush=True)
        if not path.is_file():
            continue
        agents = e["agents"]
        ours = next((i for i, a in enumerate(agents) if a.get("submissionId") == args.submission), None)
        if ours is None:
            continue
        opp = agents[1 - ours]
        row = {
            "episode_id": e["id"], "create_time": e["createTime"], "end_time": e.get("endTime"),
            "seat": ours, "our_reward": agents[ours].get("reward"), "opp_reward": opp.get("reward"),
            "our_initial_score": agents[ours].get("initialScore"), "our_updated_score": agents[ours].get("updatedScore"),
            "opp_submission_id": opp.get("submissionId"), "opp_team_id": opp.get("teamId"),
            "opp_team_name": teams.get(opp.get("teamId")), "opp_score": opp.get("initialScore"),
            "file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        r0, r1 = row["our_reward"], row["opp_reward"]
        row["result"] = None if r0 is None or r1 is None else ("W" if r0 > r1 else "L" if r0 < r1 else "T")
        rows.append(row)
    manifest = {"submission_id": args.submission, "pulled_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "episodes_listed": len(episodes), "episodes_downloaded": len(rows),
                "record": {"W": sum(r["result"] == "W" for r in rows), "L": sum(r["result"] == "L" for r in rows),
                           "T": sum(r["result"] == "T" for r in rows)},
                "episodes": rows}
    mpath = ROOT / "experiments" / f"online_{args.submission}_episodes_manifest.json"
    mpath.write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"downloaded {len(rows)} | record {manifest['record']} | manifest {mpath.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
