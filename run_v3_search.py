"""Checkpointed V2-primary raw/tail/branch search for V3."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import json
import os
from pathlib import Path
from runpy import run_path
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed

from kaggle_environments import make

from run_epic_experiments import _independent_shop_schedule, _recorded_shop_schedule
import run_super_replay_search as engine


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "agents/super_replay_v3/index.json"
MANIFEST = ROOT / "experiments/v3_top10_development_manifest.json"
OUTPUT = ROOT / "experiments/v3_candidate_search.json"
PARTIAL = ROOT / "experiments/v3_candidate_search.json.partial"
V2 = "submission/main.py"


def _trace(path, player): return f"trace:{ROOT / path}:{int(player)}"


def _compact_game(row):
    """Drop bulky per-step transition diagnostics after each completed game."""
    keep = {
        "key", "candidate", "group", "opponent", "seed", "seat", "shop_mode",
        "money", "opponent_money", "advantage", "calls", "runtime_error",
        "semantic_failures", "stranded_value", "livestock_losses", "final_weeds",
        "route_matches", "route_requests", "weed_repairs", "repair_abort", "fallback_step",
        "checkpoints",
    }
    return {key: value for key, value in row.items() if key in keep}


def _run_lean(job):
    """Equivalent evaluator without materializing env.toJSON transition data."""
    key,path,group,opponent,opponent_spec,seed,seat,schedule,config=job
    candidate=run_path(str(ROOT/path))["agent"]
    rival=engine._load_opponent(opponent_spec)
    calls=0;semantic=[];bought=Counter();checkpoints={}
    def checked(obs):
        nonlocal calls
        if int(obs["step"]) in {160,240,336,504}:
            me=obs["farms"][obs["player"]];other=obs["farms"][1-obs["player"]]
            checkpoints[str(obs["step"])]=deepcopy({
                "money":float(me["money"]),"land":len(me["unlocked_quadrants"]),"hands":len(me["hands"]),
                "shed":obs["private"]["shed"],"seeds":obs["private"]["seeds"],
                "market_prices":obs["market"]["prices"],"market_inventory":obs["market"]["inventory"],
                "opponent_money":float(other["money"]),
            })
        action=candidate(obs);calls+=1
        try: engine._semantic_validate(obs,action)
        except Exception as error: semantic.append({"step":int(obs["step"]),"error":repr(error),"action":action})
        for order in action.get("market",[]):
            if order and order[0]=="BUY_ANIMAL": bought[order[1]]+=int(order[2])
        return action
    pair=[rival,rival];pair[seat]=checked
    env=make("kaggriculture",configuration={"episodeSteps":720,"seed":int(seed),**config},debug=True)
    runtime=None
    try:
        env.run(pair) if schedule is None else engine._run_with_fixed_shops(env,pair,schedule)
    except Exception as error: runtime=repr(error)
    if runtime or len(env.steps)!=720:
        return {"key":key,"candidate":path,"group":group,"opponent":opponent,"seed":seed,"seat":seat,
                "runtime_error":runtime or f"steps={len(env.steps)}","semantic_failures":semantic}
    final=env.steps[-1]; stranded_value,_=engine._inventory_value(final[seat])
    _,animals,weeds=engine._farm_counts(final[seat].observation["farms"][seat])
    telemetry=deepcopy(candidate.telemetry)
    losses={animal:max(0,bought[animal]-animals[animal]) for animal in ("GOOSE","COW","SHEEP")}
    return {"key":key,"candidate":path,"group":group,"opponent":opponent,"seed":int(seed),"seat":int(seat),
        "shop_mode":"fixed" if schedule is not None else "natural","money":float(final[seat].reward),
        "opponent_money":float(final[1-seat].reward),"advantage":float(final[seat].reward)-float(final[1-seat].reward),
        "calls":calls,"runtime_error":None,"semantic_failures":semantic,"stranded_value":stranded_value,
        "livestock_losses":losses,"final_weeds":weeds,"route_matches":telemetry["all_route_matches"],
        "route_requests":telemetry["all_route_requests"],"weed_repairs":telemetry["repairs"]["weed"],
        "repair_abort":telemetry["repair_abort"],"fallback_step":telemetry.get("fallback_step"),"checkpoints":checkpoints}


def _run_compact(job):
    return _compact_game(_run_lean(job))


def _traces(maximum):
    manifest = json.loads(MANIFEST.read_text())
    by_submission = {}
    for episode in manifest["episodes"]:
        if not episode["replay_valid"]: continue
        for app in episode["appearances"]:
            if not app["is_selected_elite_submission"]: continue
            sid = app["submission_id"]
            current = by_submission.get(sid)
            key = (app["leaderboard_rank"] or 999, -float(app["reward"]), episode["episode_id"])
            if current is None or key < current[0]: by_submission[sid] = (key, episode, app)
    selected = sorted(by_submission.values(), key=lambda x: x[0])[:maximum]
    rows=[]
    for _,episode,app in selected:
        replay=json.loads((ROOT/episode["replay_path"]).read_text())
        rows.append({"name":f"rank{app['leaderboard_rank']}_{app['submission_id']}_{episode['episode_id']}",
            "path":episode["replay_path"],"player":app["seat"],"seed":episode["seed"],
            "schedule":_recorded_shop_schedule(replay)})
    return rows


def jobs(candidates, mode):
    seeds = range(996100,996102) if mode=="cheap" else range(996200,996204)
    traces = _traces(4)
    rows=[]
    for name,path in candidates.items():
        for seed in seeds:
            for seat in (0,1):
                rows.append((f"{mode}|{name}|v2f|{seed}|{seat}",path,"direct_v2_fixed","V2",V2,seed,seat,_independent_shop_schedule(seed),{}))
                rows.append((f"{mode}|{name}|v2n|{seed}|{seat}",path,"direct_v2_natural","V2",V2,seed,seat,None,{}))
        for trace in traces:
            for seat in (0,1):
                rows.append((f"{mode}|{name}|{trace['name']}|{seat}",path,"development_elite_trace",trace["name"],
                    _trace(trace["path"],trace["player"]),trace["seed"],seat,trace["schedule"],{}))
    return rows,traces


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--mode",choices=("cheap","serious"),default="cheap")
    parser.add_argument("--names",default="");parser.add_argument("--workers",type=int,default=2)
    parser.add_argument("--output",default="");parser.add_argument("--partial",default="")
    parser.add_argument("--isolated",action="store_true")
    parser.add_argument("--compact-parallel",action="store_true")
    parser.add_argument("--job-json");parser.add_argument("--job-output")
    args=parser.parse_args();index=json.loads(INDEX.read_text())
    if args.job_json:
        result=_compact_game(_run_lean(tuple(json.loads(args.job_json))))
        Path(args.job_output).write_text(json.dumps(result,separators=(",",":")))
        return
    if args.names:
        selected=set(args.names.split(","));index={k:v for k,v in index.items() if k in selected}
    run_jobs,traces=jobs(index,args.mode)
    engine.PARTIAL=Path(args.partial).resolve() if args.partial else PARTIAL
    if args.compact_parallel:
        partial=Path(args.partial).resolve() if args.partial else PARTIAL
        games=[_compact_game(row) for row in json.loads(partial.read_text()).get("games",[])] if partial.exists() else []
        done={row["key"] for row in games};todo=[job for job in run_jobs if job[0] not in done]
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures=[pool.submit(_run_compact,job) for job in todo]
            for position,future in enumerate(as_completed(futures),1):
                games.append(future.result())
                if position%10==0 or position==len(futures):
                    partial.write_text(json.dumps({"schema_version":1,"games":games})+"\n")
                    print(f"games {position}/{len(futures)} total={len(games)}",flush=True)
    elif args.isolated:
        partial=Path(args.partial).resolve() if args.partial else PARTIAL
        games=[_compact_game(row) for row in json.loads(partial.read_text()).get("games",[])] if partial.exists() else []
        done={row["key"] for row in games};todo=[job for job in run_jobs if job[0] not in done]
        with tempfile.TemporaryDirectory(prefix="v3-search-") as raw:
            directory=Path(raw)
            for position,job in enumerate(todo,1):
                target=directory/f"{position}.json"
                completed=subprocess.run([sys.executable,str(Path(__file__).resolve()),"--job-json",json.dumps(job,separators=(",",":")),"--job-output",str(target)],cwd=ROOT,text=True,capture_output=True,timeout=240,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
                if completed.returncode: raise RuntimeError(f"job {job[0]}: {completed.stderr or completed.stdout}")
                games.append(json.loads(target.read_text()))
                if position%1==0 or position==len(todo):
                    partial.write_text(json.dumps({"schema_version":1,"games":games})+"\n")
                    print(f"games {position}/{len(todo)} total={len(games)}",flush=True)
    else:
        games=engine._run_jobs(run_jobs,args.workers)
    payload={"schema_version":1,"mode":args.mode,"primary_baseline":V2,"candidates":index,
        "traces":traces,"jobs_expected":len(run_jobs),"games":games,"summary":engine._summaries(games)}
    target=Path(args.output).resolve() if args.output else OUTPUT
    target.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    for path,row in sorted(payload["summary"].items(),key=lambda x:x[1]["average_advantage"],reverse=True):
        print(path,row["games"],row["wins"],row["losses"],round(row["average_money"],1),round(row["average_advantage"],1),round(row["p10"],1),round(row["p5"],1),row["livestock_losses"])


if __name__=="__main__": main()
