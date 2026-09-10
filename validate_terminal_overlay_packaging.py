"""Compact action/state/money equivalence for research vs packaged terminal agent."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

from kaggle_environments import make
from run_epic_experiments import _run_with_fixed_shops


ROOT = Path(__file__).resolve().parent
RESEARCH = ROOT / "agents/shop_router_0909_terminal/main.py"
PACKAGED = ROOT / "submission/main.py"
TMP = Path("/private/tmp/lb_gap_opponents")
OPPONENTS = {
    "market_smart_terminal": TMP / "market_smart/main.py",
    "most_powerfull_terminal": TMP / "most_powerfull/main.py",
    "farming_v3_current": TMP / "farming_v3_current/main.py",
    "shape_shop_current": TMP / "shape_shop_current/main.py",
    "v2": ROOT / "agents/super_replay_v2/super_backbone_v2.py",
}
CONDITIONS = [
    ("market_smart_terminal",2609300,0,None),("market_smart_terminal",2609300,1,None),
    ("most_powerfull_terminal",2609300,0,None),("most_powerfull_terminal",2609300,1,None),
    ("farming_v3_current",2609400,0,None),("farming_v3_current",2609400,1,None),
    ("shape_shop_current",2609400,0,None),("shape_shop_current",2609400,1,None),
    ("v2",2609500,0,("YARN_STORE","PET_CAFE")),("v2",2609500,1,("YARN_STORE","PET_CAFE")),
]


def load(path, tag):
    name=f"terminal_package_{tag}_{time.time_ns()}"
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module.agent


def fixed_schedule(pair):
    first,second=pair
    return {day:([first] if day>=3 else [])+([second] if day>=6 else []) for day in range(30)}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),default=str).encode()).hexdigest()


def execute(job):
    variant,opponent_name,seed,seat,fixed_pair=job
    actions=[];errors=[]
    candidate=load(RESEARCH if variant=="research" else PACKAGED,f"{variant}_{seed}_{seat}")
    opponent=load(OPPONENTS[opponent_name],f"opponent_{opponent_name}_{seed}_{seat}")
    def traced(obs,config=None):
        try: action=candidate(obs,config)
        except Exception as exc:
            errors.append({"step":int(obs["step"]),"error":repr(exc)});raise
        actions.append(deepcopy(action));return action
    pair=[opponent,opponent];pair[seat]=traced
    env=make("kaggriculture",configuration={"episodeSteps":720,"seed":seed},debug=False)
    run_error=None
    try:
        if fixed_pair:_run_with_fixed_shops(env,pair,fixed_schedule(fixed_pair))
        else:env.run(pair)
    except Exception as exc:run_error=repr(exc)
    if run_error or len(env.steps)!=720:
        return {"variant":variant,"opponent":opponent_name,"seed":seed,"seat":seat,"fixed_pair":list(fixed_pair) if fixed_pair else None,"runtime_error":run_error or f"steps={len(env.steps)}","errors":errors}
    final=env.steps[-1]
    final_state=[final[i].observation for i in range(2)]
    return {"variant":variant,"opponent":opponent_name,"seed":seed,"seat":seat,"fixed_pair":list(fixed_pair) if fixed_pair else None,"runtime_error":None,"errors":errors,"action_count":len(actions),"action_sha256":digest(actions),"final_state_sha256":digest(final_state),"rewards":[float(final[i].reward) for i in range(2)],"statuses":[str(final[i].status) for i in range(2)]}


def main():
    jobs=[(v,*c) for c in CONDITIONS for v in ("research","packaged")]
    rows=[]
    with ProcessPoolExecutor(max_workers=6) as pool:
        for f in as_completed([pool.submit(execute,j) for j in jobs]):rows.append(f.result())
    pairs=[]
    for condition in CONDITIONS:
        op,seed,seat,fixed=condition
        pick=lambda v:next(r for r in rows if r["variant"]==v and (r["opponent"],r["seed"],r["seat"],tuple(r.get("fixed_pair") or ()))==(op,seed,seat,tuple(fixed or ())))
        a,b=pick("research"),pick("packaged")
        pairs.append({"opponent":op,"seed":seed,"seat":seat,"fixed_pair":list(fixed) if fixed else None,"action_mismatch":a.get("action_sha256")!=b.get("action_sha256"),"final_state_mismatch":a.get("final_state_sha256")!=b.get("final_state_sha256"),"final_money_mismatch":a.get("rewards")!=b.get("rewards"),"research":a,"packaged":b})
    result={"schema_version":1,"conditions":len(pairs),"games":len(rows),"action_mismatches":sum(p["action_mismatch"] for p in pairs),"final_state_mismatches":sum(p["final_state_mismatch"] for p in pairs),"final_money_mismatches":sum(p["final_money_mismatch"] for p in pairs),"runtime_errors":sum(r.get("runtime_error") is not None for r in rows),"agent_errors":sum(len(r.get("errors",[])) for r in rows),"all_equivalent":all(not p["action_mismatch"] and not p["final_state_mismatch"] and not p["final_money_mismatch"] for p in pairs),"pairs":pairs}
    (ROOT/"experiments/terminal_overlay_packaging_equivalence.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:result[k] for k in ("conditions","games","action_mismatches","final_state_mismatches","final_money_mismatches","runtime_errors","agent_errors","all_equivalent")},indent=2))


if __name__=="__main__":main()
