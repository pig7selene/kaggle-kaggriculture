"""Walk the ladder from our opponents to the teams we want to study.

Kaggle's public `ListEpisodes` takes a submissionId and returns, for every
episode, both agents' submissionId, teamId and scores plus a teamId -> name map.
Our own episode manifests therefore already hold the current submission of
every opponent we met, and each of those submissions' episodes hold theirs. A
breadth-first walk of a few hops reaches the 2900 band and the top teams,
giving their live submission ids without any login. Their latest replays then
come from the same replay.json endpoint we use for our own.
"""
from __future__ import annotations
import argparse, json, time, urllib.request
from collections import deque
import heapq
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LIST_URL = "https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes"
TARGETS = {"Driz Lo", "Thomas Tschinkel", "Catalyst", "mikelou1", "Kaggriculture Agent", "Majkel1337",
           "M & M & P & Q", "DSM", "SpaTaro", "ymg_aq", "THIRD FARM CLUB", "Arda Ceylan", "feel the agi"}


def list_episodes(submission):
    req = urllib.request.Request(LIST_URL, data=json.dumps({"submissionId": int(submission)}).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", default="56296489,56293133")
    ap.add_argument("--hops", type=int, default=3)
    ap.add_argument("--max-requests", type=int, default=160)
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--out", default="experiments/submission_graph.json")
    a = ap.parse_args()
    out = ROOT / a.out
    known = json.loads(out.read_text()) if out.is_file() else {"submissions": {}, "teams": {}}
    subs, teams = known["submissions"], known["teams"]
    # best-first: expand the highest-rated known submission next, so the walk
    # climbs the ladder instead of sweeping the 2200 band
    queue = [(0.0, int(s), 0) for s in a.seeds.split(",")]
    for k, v in subs.items():
        if not v.get("expanded") and v.get("latest_score"):
            queue.append((-float(v["latest_score"]), int(k), v.get("hop", 1)))
    heapq.heapify(queue)
    seen = set(int(k) for k in subs)
    requests = 0
    found = {}
    while queue and requests < a.max_requests:
        _, sid, hop = heapq.heappop(queue)
        if sid in seen and str(sid) in subs and subs[str(sid)].get("expanded"):
            continue
        try:
            data = list_episodes(sid)
        except Exception as exc:
            print(f"  {sid}: error {exc}", flush=True)
            continue
        requests += 1
        time.sleep(a.sleep)
        for t in (data.get("teams") or []):
            if isinstance(t, dict) and t.get("id") is not None:
                teams[str(t["id"])] = {"name": t.get("teamName"), "public_submission": t.get("publicLeaderboardSubmissionId"),
                                      "last_submission": t.get("lastSubmissionDate"), "submission_count": t.get("submissionCount")}
        eps = data.get("episodes") or []
        rec = subs.setdefault(str(sid), {})
        rec.update({"expanded": True, "hop": hop, "episodes": len(eps)})
        latest = None
        for e in eps:
            for ag in e.get("agents") or []:
                osid, otid = ag.get("submissionId"), ag.get("teamId")
                if osid is None:
                    continue
                r = subs.setdefault(str(osid), {})
                r["team_id"] = otid
                r["team_name"] = (teams.get(str(otid)) or {}).get("name", r.get("team_name"))
                r["public_submission"] = (teams.get(str(otid)) or {}).get("public_submission")
                r["last_submission"] = (teams.get(str(otid)) or {}).get("last_submission")
                sc = ag.get("updatedScore") or ag.get("initialScore")
                ct = e.get("createTime") or e.get("endTime")
                if sc is not None and (r.get("latest_time") is None or (ct or "") >= (r.get("latest_time") or "")):
                    r["latest_score"] = sc
                    r["latest_time"] = ct
                if osid == sid:
                    latest = ct if (latest is None or (ct or "") > latest) else latest
                if osid not in seen and hop < a.hops:
                    seen.add(osid)
                    heapq.heappush(queue, (-float(sc or 0), osid, hop + 1))
        rec["latest_episode_time"] = latest
        name = rec.get("team_name")
        if name in TARGETS:
            found.setdefault(name, []).append(sid)
        print(f"hop {hop} sub {sid} {str(name)[:22]:22s} score {rec.get('latest_score')} eps {len(eps)} | queue {len(queue)} | targets found {sorted(found)}", flush=True)
        out.write_text(json.dumps({"submissions": subs, "teams": teams}, indent=0) + "\n")
    print("\n=== target teams: current public submission (from the teams map) ===")
    for tid, t in sorted(teams.items(), key=lambda kv: str(kv[1].get("name"))):
        if t.get("name") in TARGETS:
            print(f"  {t.get('name'):22s} team {tid} public_submission {t.get('public_submission')} last_submission {str(t.get('last_submission'))[:19]} submissions {t.get('submission_count')}")
    print(f"requests {requests}, submissions known {len(subs)}, teams {len(teams)}")


if __name__ == "__main__":
    main()
