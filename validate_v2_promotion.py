"""Validate promoted V2 wrapper against its locked raw finalist."""

from copy import deepcopy
import json
from pathlib import Path
from runpy import run_path

from kaggle_environments import make

from run_epic_experiments import _independent_shop_schedule, _run_with_fixed_shops
from run_v27_replay_backbone import _inventory_value, _semantic_validate


ROOT=Path(__file__).resolve().parent
RAW="agents/super_replay_v2/v2_raw_55463387.py"
PROMOTED="agents/super_replay_v2/super_backbone_v2.py"
V1="agents/super_replay/super_backbone_v1.py"
OUTPUT=ROOT/"experiments/v2_promotion_validation.json"


def _run(path,seed,seat):
    candidate=run_path(str(ROOT/path))["agent"]; rival=run_path(str(ROOT/V1))["agent"]
    actions=[]; semantic=[]
    def checked(obs):
        action=candidate(obs); actions.append(deepcopy(action))
        try:_semantic_validate(obs,action)
        except Exception as error:semantic.append({"step":int(obs["step"]),"error":repr(error)})
        return action
    pair=[rival,rival];pair[seat]=checked
    env=make("kaggriculture",configuration={"episodeSteps":720,"seed":seed},debug=True)
    runtime=None
    try:_run_with_fixed_shops(env,pair,_independent_shop_schedule(seed))
    except Exception as error:runtime=repr(error)
    final=env.steps[-1]; stranded_value,stranded=_inventory_value(final[seat]); telemetry=deepcopy(candidate.telemetry)
    return {"actions":actions,"runtime_error":runtime,"semantic_failures":semantic,"steps":len(env.steps),"money":float(final[seat].reward),"opponent_money":float(final[1-seat].reward),"stranded_value":stranded_value,"stranded":stranded,"telemetry":telemetry}


def main():
    games=[]
    for seed,seat in ((995700,0),(995701,1)):
        raw=_run(RAW,seed,seat); promoted=_run(PROMOTED,seed,seat)
        diffs=[i for i,(a,b) in enumerate(zip(raw["actions"],promoted["actions"])) if a!=b]
        games.append({"seed":seed,"seat":seat,"compared_actions":min(len(raw["actions"]),len(promoted["actions"])),"action_differences":diffs,"raw":{k:v for k,v in raw.items() if k!="actions"},"promoted":{k:v for k,v in promoted.items() if k!="actions"}})
    passed=all(r["compared_actions"]==719 and not r["action_differences"] and r["raw"]==r["promoted"] for r in games)
    OUTPUT.write_text(json.dumps({"schema_version":1,"raw":RAW,"promoted":PROMOTED,"games":games,"passed":passed},indent=2,sort_keys=True)+"\n")
    print(json.dumps({"passed":passed,"games":[{"seed":r["seed"],"seat":r["seat"],"actions":r["compared_actions"],"money":r["promoted"]["money"]} for r in games]},indent=2))


if __name__=="__main__":main()
