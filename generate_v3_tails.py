"""Generate only V2-compatible coherent tails from current Top-10 routes."""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from runpy import run_path

from generate_super_splices import _state_distance
import package_v27_submission as template


ROOT=Path(__file__).resolve().parent
V2_BANK=ROOT/"experiments/v2_route_executor.json"
V3_BANK=ROOT/"experiments/v3_route_executor.json"
INDEX=ROOT/"agents/super_replay_v3/index.json"
GRAPH=ROOT/"experiments/v3_tail_graph.json"
OUT=ROOT/"agents/super_replay_v3"
CHECKPOINTS=(160,192,240,264,288,312,336,360,408,456,504,552,600,648)


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def main():
    v2=next(x for x in json.loads(V2_BANK.read_text())["routes"] if x["route_id"]=="super_raw_55463387")
    bank=json.loads(V3_BANK.read_text()); donors=[x for x in bank["routes"] if x.get("family_id")=="v3_family_01"]
    distances=[];specs=[]
    for donor in donors:
        for step in CHECKPOINTS:
            value=_state_distance(v2["expected_state"][step],donor["expected_state"][step])
            distances.append({"donor":donor["route_id"],"step":step,"distance":value,"compatible":value<=1.5})
            if value<=1.5:specs.append((value,donor,step))
    specs.sort(key=lambda x:(x[0],x[2],x[1]["route_id"]))
    generated=[];seen=set()
    for value,donor,step in specs:
        actions=deepcopy(v2["consensus_actions"][:step])+deepcopy(donor["consensus_actions"][step:])
        fingerprint=digest(actions)
        if fingerprint in seen:continue
        seen.add(fingerprint);name=f"v3_tail_{donor['source_submission_id']}_{step}"
        route={"route_id":name,"family_id":"v3_compatible_tail","source_submission_id":donor["source_submission_id"],
            "source_team":f"V2->{donor['source_team']}","source_episode_id":donor["source_episode_id"],
            "source_player":donor["source_player"],"source_seed":donor["source_seed"],"source_replay_path":donor["source_replay_path"],
            "source_final_money":donor["source_final_money"],"consensus_actions":actions,
            "expected_state":deepcopy(v2["expected_state"][:step])+deepcopy(donor["expected_state"][step:]),
            "milestones":v2.get("milestones",{}),"splice":{"from":"super_raw_55463387","to":donor["route_id"],"step":step,"entry_distance":value},
            "action_sha256":fingerprint}
        generated.append(route)
        if len(generated)>=24:break
    bank["routes"].extend(generated);bank["route_count"]=len(bank["routes"]);V3_BANK.write_text(json.dumps(bank,separators=(",",":"))+"\n")
    index=json.loads(INDEX.read_text())
    for route in generated:
        path=OUT/f"{route['route_id']}.py"
        template.SOURCE=ROOT/"agents/super_replay_v2/super_backbone_v2.py";template.MANIFEST=V3_BANK;template.OUTPUT=path
        template.EXPECTED_SOURCE_SHA="c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef";template.ROUTE_ID=route["route_id"]
        template.main();index[route["route_id"]]=str(path.relative_to(ROOT));assert run_path(str(path))["agent"].route["route_id"]==route["route_id"]
    INDEX.write_text(json.dumps(index,indent=2,sort_keys=True)+"\n")
    GRAPH.write_text(json.dumps({"schema_version":1,"compatibility_threshold":1.5,"distances":distances,
        "generated":[{"route_id":x["route_id"],**x["splice"]} for x in generated]},indent=2,sort_keys=True)+"\n")
    print(f"donors={len(donors)} compatible={len(specs)} generated={len(generated)}")


if __name__=="__main__":main()
