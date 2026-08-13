"""Memory-bounded Top-10 route mining for V3 development only."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import statistics

from analyze_super_replays import _counts, _milestones
from analyze_v27_routes import normalized_action, state_anchor


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "experiments/v3_top10_development_manifest.json"
STABILITY = ROOT / "experiments/v3_route_stability.json"
FAMILIES = ROOT / "experiments/v3_route_families.json"
ROUTE_BANK = ROOT / "experiments/v3_route_bank.json"
EXECUTOR = ROOT / "experiments/v3_route_executor.json"
DIVERGENCES = ROOT / "experiments/v3_within_submission_divergences.json"
PHASES = {
    "opening": (0, 160), "first_expansion": (160, 240),
    "second_expansion": (240, 336), "midgame": (336, 504),
    "late_game": (504, 648), "liquidation": (648, 719),
}
CHECKPOINTS = (0, 96, 144, 192, 240, 264, 336, 360, 480, 504, 600, 648, 696, 718)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def target_tokens(replay, player, actions):
    rows = []
    for step, action in enumerate(actions):
        farm = replay["steps"][step][player]["observation"]["farms"][player]
        positions = [farm["farmer"], *farm.get("hands", [])]
        rows.append([[req[0], pos[0], pos[1]] for pos, req in zip(positions, [action["farmer"], *action["hands"]])])
    return rows


def appearance(path, player, meta):
    replay = json.loads(path.read_text())
    actions = [normalized_action(replay, player, step) for step in range(719)]
    anchors = []
    for step in range(719):
        state = state_anchor(replay, player, step)
        state.update(_counts(replay["steps"][step][player]["observation"]["farms"][player]))
        anchors.append(state)
    return {
        **meta, "player": player, "path": str(path.relative_to(ROOT)),
        "seed": int(replay["info"]["seed"]),
        "opponent": replay["info"]["TeamNames"][1-player],
        "money": float(replay["steps"][-1][player]["reward"]),
        "opponent_money": float(replay["steps"][-1][1-player]["reward"]),
        "actions": actions, "anchors": anchors,
        "targets": target_tokens(replay, player, actions),
        "milestones": _milestones(actions, anchors),
        "action_hash": digest(actions),
    }


def component(action, name):
    if name == "farmer": return action["farmer"]
    if name == "worker": return action["hands"]
    if name == "field": return [action["farmer"], *action["hands"]]
    if name == "market": return action["market"]
    if name == "sell": return [x for x in action["market"] if x and x[0] == "SELL"]
    raise KeyError(name)


def modal_stability(rows, getter, lo, hi):
    return statistics.fmean(
        Counter(canonical(getter(row, step)) for row in rows).most_common(1)[0][1] / len(rows)
        for step in range(lo, hi)
    )


def similarity(left, right):
    return sum(a == b for a, b in zip(left["actions"], right["actions"])) / 719


def vector(row):
    out = []
    for step in CHECKPOINTS:
        a = row["anchors"][step]
        out += [a.get("hand_count", 0)/15, len(a.get("quadrants", []))/4,
                a.get("animals", {}).get("COW", 0)/10, a.get("animals", {}).get("SHEEP", 0)/10,
                a.get("crops", {}).get("WHEAT", 0)/75, a.get("crops", {}).get("MELON", 0)/75,
                a.get("crops", {}).get("STRAWBERRY", 0)/75, a.get("productive", 0)/100]
    return out


def distance(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b))/len(a))


def observable(row, step):
    replay = json.loads((ROOT / row["path"]).read_text())
    obs = replay["steps"][step][row["player"]]["observation"]
    anchor = row["anchors"][step]
    opp = _counts(obs["farms"][1-row["player"]])
    products = ("MILK", "WOOL", "STRAWBERRY", "MELON", "WHEAT")
    old = replay["steps"][max(0, step-24)][row["player"]]["observation"]["market"]["prices"]
    return {
        "bank": anchor["money"], "land_count": len(anchor["quadrants"]),
        "hand_count": anchor["hand_count"], "animals": anchor["animals"],
        "crops": anchor["crops"], "productive": anchor["productive"],
        "shed": anchor.get("shed", {}), "seeds": anchor.get("seeds", {}),
        "market_prices": {p: obs["market"]["prices"][p] for p in products},
        "market_change_24": {p: obs["market"]["prices"][p]-old[p] for p in products},
        "opponent_crops": opp["crops"], "opponent_animals": opp["animals"],
        "opponent_productive": opp["productive"], "weeds": anchor["weeds"],
    }


def main():
    manifest = json.loads(MANIFEST.read_text())
    appearances = defaultdict(list)
    submission_info = {int(x["selected_submission_id"]): x for x in manifest["submissions"]}
    for episode in manifest["episodes"]:
        if not episode["replay_valid"]: continue
        for app in episode["appearances"]:
            if not app["is_selected_elite_submission"]: continue
            sid = int(app["submission_id"])
            appearances[sid].append((episode, app))

    stability_rows, routes, divergence_rows = [], [], []
    for index, (sid, pairs) in enumerate(sorted(appearances.items(), key=lambda x: submission_info[x[0]]["rank"]), 1):
        # Exact duplicate action trajectories add no stability information.
        loaded, seen = [], set()
        for episode, app in pairs:
            key = app.get("action_hash")
            if key in seen: continue
            seen.add(key)
            path = ROOT / episode["replay_path"]
            loaded.append(appearance(path, int(app["seat"]), {
                "episode_id": episode["episode_id"], "submission_id": sid,
                "team": app["team_name"], "rank": app["leaderboard_rank"],
                "score": app["leaderboard_score"],
            }))
        medoid = max(loaded, key=lambda row: sum(similarity(row, other) for other in loaded))
        phases = {}
        for phase, (lo, hi) in PHASES.items():
            phases[phase] = {
                name: modal_stability(loaded, (lambda row, step, name=name: component(row["actions"][step], name)), lo, hi)
                for name in ("farmer", "worker", "field", "market", "sell")
            }
            phases[phase]["spatial_target"] = modal_stability(loaded, lambda row, step: row["targets"][step], lo, hi)
        field_min = min(v["field"] for v in phases.values()); market_avg = statistics.fmean(v["market"] for v in phases.values())
        classification = ("fixed" if field_min >= .97 and market_avg >= .94 else
                          "fixed_bounded_repair" if field_min >= .90 else
                          "phase_adaptive" if field_min >= .70 else
                          "branch_adaptive" if field_min >= .45 else "strongly_adaptive")
        schedule = {}
        for key in medoid["milestones"]:
            vals = [r["milestones"].get(key) for r in loaded]
            mode, count = Counter(str(v) for v in vals).most_common(1)[0]
            schedule[key] = {"mode": None if mode == "None" else int(float(mode)), "stability": count/len(vals),
                             "values": vals}
        stability_rows.append({
            "submission_id": sid, "team_name": medoid["team"], "rank": medoid["rank"], "score": medoid["score"],
            "appearances": len(loaded), "classification": classification, "stability": phases,
            "schedule_stability": schedule, "representative_episode": medoid["episode_id"],
            "average_final_money": statistics.fmean(r["money"] for r in loaded),
            "median_final_money": statistics.median(r["money"] for r in loaded),
            "route_hashes": Counter(r["action_hash"] for r in loaded).most_common(),
        })
        route_id = f"v3_raw_{sid}"
        routes.append({
            "route_id": route_id, "source_submission_id": sid, "source_team": medoid["team"],
            "source_episode_id": medoid["episode_id"], "source_player": medoid["player"],
            "source_seed": medoid["seed"], "source_replay_path": medoid["path"],
            "source_final_money": medoid["money"], "source_opponent": medoid["opponent"],
            "appearance_count": len(loaded), "average_source_money": statistics.fmean(r["money"] for r in loaded),
            "stability_class": classification, "consensus_actions": medoid["actions"],
            "expected_state": medoid["anchors"], "milestones": medoid["milestones"],
            "action_sha256": digest(medoid["actions"]), "structural_vector": vector(medoid),
        })
        for row in loaded:
            if row["episode_id"] == medoid["episode_id"]: continue
            step = next((s for s in range(719) if row["actions"][s] != medoid["actions"][s]), None)
            if step is None: continue
            divergence_rows.append({
                "submission_id": sid, "team": medoid["team"], "episode_id": row["episode_id"],
                "representative_episode": medoid["episode_id"], "first_divergence_step": step,
                "state_before_divergence": observable(row, step), "branch_chosen": row["actions"][step],
                "default_action": medoid["actions"][step], "later_final_money": row["money"],
                "representative_final_money": medoid["money"], "causal_status": "observational_only",
            })
        print(f"streamed submission {index}/{len(appearances)} {sid} {classification}", flush=True)
        del loaded

    # Natural structural route families.
    parent = {r["route_id"]: r["route_id"] for r in routes}
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b: parent[b]=a
    pairwise=[]
    for i,a in enumerate(routes):
        for b in routes[i+1:]:
            d=distance(a["structural_vector"],b["structural_vector"]);pairwise.append({"left":a["route_id"],"right":b["route_id"],"distance":d})
            if d <= .10: union(a["route_id"],b["route_id"])
    groups=defaultdict(list)
    for r in routes: groups[find(r["route_id"])].append(r)
    family_rows=[]
    for idx,values in enumerate(sorted(groups.values(),key=lambda x:(-len(x),min(r["source_submission_id"] for r in x))),1):
        fid=f"v3_family_{idx:02d}"
        for r in values:r["family_id"]=fid
        family_rows.append({"family_id":fid,"size":len(values),"route_ids":[r["route_id"] for r in values],
                            "submission_ids":[r["source_submission_id"] for r in values],"teams":[r["source_team"] for r in values],
                            "ranks":[next(s["rank"] for s in stability_rows if s["submission_id"]==r["source_submission_id"]) for r in values]})
    for r in routes:r.pop("structural_vector",None)
    STABILITY.write_text(json.dumps({"schema_version":1,"submission_count":len(stability_rows),
        "unique_selected_appearances_after_action_dedup":sum(r["appearances"] for r in stability_rows),"submissions":stability_rows},indent=2,ensure_ascii=False)+"\n")
    FAMILIES.write_text(json.dumps({"schema_version":1,"family_count":len(family_rows),"threshold":.10,
        "families":family_rows,"pairwise":pairwise},indent=2,ensure_ascii=False)+"\n")
    DIVERGENCES.write_text(json.dumps({"schema_version":1,"records":divergence_rows,
        "submissions_with_divergence":len({r["submission_id"] for r in divergence_rows}),
        "note":"Observable first divergences; observational only until paired counterfactual validation."},indent=2,ensure_ascii=False)+"\n")
    ROUTE_BANK.write_text(json.dumps({"schema_version":1,"route_count":len(routes),"routes":routes},indent=2,ensure_ascii=False)+"\n")
    EXECUTOR.write_text(json.dumps({"schema_version":1,"route_count":len(routes),"routes":routes},separators=(",",":"))+"\n")
    print(json.dumps({"submissions":len(routes),"appearances":sum(r["appearances"] for r in stability_rows),"families":len(family_rows)},indent=2))


if __name__ == "__main__": main()
