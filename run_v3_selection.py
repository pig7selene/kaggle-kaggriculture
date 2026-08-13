"""Strict selection and hash-locked final validation for V3."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from run_epic_experiments import _independent_shop_schedule, _recorded_shop_schedule
import run_v3_search as search
import run_super_replay_search as engine


ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/"experiments/v3_top10_corpus_manifest.json"
SELECTION=ROOT/"experiments/v3_selection_results.json"
FINAL=ROOT/"experiments/v3_final_validation.json"
LOCK=ROOT/"experiments/v3_finalist_lock.json"
V2="submission/main.py"
CANDIDATES={
    "V2":V2,
    "always_tail":"agents/super_replay_v3/v3_tail_55474695_160.py",
    "branch_bank644":"agents/super_replay_v3/v3_branch_opponent_bank_644.py",
}


def sha(path):return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def trace(path,player):return f"trace:{ROOT/path}:{int(player)}"


def traces(split,maximum):
    m=json.loads(MANIFEST.read_text());ids=set(m["splits"][f"{split}_episode_ids"]);rows=[];seen=set()
    for episode in m["episodes"]:
        if episode["episode_id"] not in ids:continue
        replay_path=f"experiments/v3_top10_corpus/replays/episode-{episode['episode_id']}-replay.json"
        replay=json.loads((ROOT/replay_path).read_text())
        for app in episode.get("appearances",[]):
            if not app.get("is_selected_elite_submission") or app["submission_id"] in seen:continue
            seen.add(app["submission_id"]);rows.append({"episode_id":episode["episode_id"],"submission_id":app["submission_id"],
                "rank":app["leaderboard_rank"],"player":app["seat"],"path":replay_path,"seed":episode["seed"],
                "schedule":_recorded_shop_schedule(replay)})
            break
        if len(rows)>=maximum:break
    return rows


def jobs(candidates,mode):
    split="selection" if mode=="selection" else "final_holdout";ts=traces(split,6 if mode=="selection" else 10)
    seeds=range(997100,997104) if mode=="selection" else range(997500,997506);rows=[]
    for name,path in candidates.items():
        for t in ts:
            for seat in (0,1):rows.append((f"{mode}|{name}|trace{t['episode_id']}|{seat}",path,f"{mode}_elite_trace",f"rank{t['rank']}_{t['submission_id']}",trace(t["path"],t["player"]),t["seed"],seat,t["schedule"],{}))
        for seed in seeds:
            for seat in (0,1):
                rows.append((f"{mode}|{name}|v2f|{seed}|{seat}",path,f"{mode}_v2_fixed","V2",V2,seed,seat,_independent_shop_schedule(seed),{}))
                rows.append((f"{mode}|{name}|v2n|{seed}|{seat}",path,f"{mode}_v2_natural","V2",V2,seed,seat,None,{}))
    return rows,ts


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--mode",choices=("selection","final"),required=True);args=parser.parse_args()
    candidates=CANDIDATES if args.mode=="selection" else {"V2":V2,"branch_bank644":CANDIDATES["branch_bank644"]}
    output=SELECTION if args.mode=="selection" else FINAL
    partial=output.with_suffix(output.suffix+".partial")
    if args.mode=="final":
        lock=json.loads(LOCK.read_text())
        for name,path in candidates.items():
            if lock["finalists"][name]["sha256"]!=sha(path):raise SystemExit(f"locked finalist changed: {name}")
    run_jobs,ts=jobs(candidates,args.mode);games=json.loads(partial.read_text()).get("games",[]) if partial.exists() else []
    done={row["key"] for row in games};todo=[job for job in run_jobs if job[0] not in done]
    for i,job in enumerate(todo,1):
        games.append(search._compact_game(search._run_lean(job)))
        partial.write_text(json.dumps({"schema_version":1,"games":games})+"\n")
        if i%5==0:print(f"{args.mode} {i}/{len(todo)} total={len(games)}",flush=True)
    payload={"schema_version":1,"mode":args.mode,"candidates":candidates,"trace_pool":ts,"jobs_expected":len(run_jobs),
        "games":games,"summary":engine._summaries(games)};output.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    if args.mode=="selection":
        LOCK.write_text(json.dumps({"schema_version":1,"selection_sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
            "policy":"Only hash-locked V2 and one-branch policy may open final holdout; no tuning afterward.",
            "finalists":{name:{"path":path,"sha256":sha(path),"branch_policy":None if name=="V2" else "step160: opponent bank <= 644 -> Furious-Monk tail; else V2"} for name,path in {"V2":V2,"branch_bank644":CANDIDATES["branch_bank644"]}.items()}},indent=2,sort_keys=True)+"\n")
    for path,row in payload["summary"].items():print(path,row["games"],row["wins"],row["losses"],round(row["average_advantage"],1),round(row["p10"],1),round(row["p5"],1),row["livestock_losses"])


if __name__=="__main__":main()
