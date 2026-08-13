"""Fingerprint high-rating public routes and build a leakage-aware route bank.

The analyzer deliberately clusters whole submission trajectories.  It never
votes across unrelated players.  A route is selected from one real appearance;
the remaining appearances are used only to classify stable versus
environment-dependent actions and to build state anchors.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import statistics
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CORPUS = ROOT / "experiments/top_player_replays"
MANIFEST_OUT = ROOT / "experiments/v27_route_manifest.json"
STABILITY_OUT = ROOT / "experiments/v27_route_stability.json"

WINDOWS = {
    "opening_0_159": (0, 160),
    "midgame_160_407": (160, 408),
    "late_408_718": (408, 719),
    "full_0_718": (0, 719),
}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def normalized_action(replay, player, step):
    action = deepcopy(replay["steps"][step + 1][player].get("action") or {})
    obs = replay["steps"][step][player]["observation"]
    hand_count = len(obs["farms"][player].get("hands", []))
    hands = list(action.get("hands", []))
    hands.extend([["PASS"]] * max(0, hand_count - len(hands)))
    return {
        "farmer": action.get("farmer", ["PASS"]),
        "hands": hands[:hand_count],
        "market": list(action.get("market", []))[:10],
    }


def action_component(action, component):
    if component == "farmer":
        return action["farmer"]
    if component == "hands":
        return action["hands"]
    if component == "field":
        return [action["farmer"], *action["hands"]]
    if component == "market":
        return action["market"]
    if component == "sell":
        return [order for order in action["market"] if order and order[0] == "SELL"]
    if component == "non_sell":
        return [order for order in action["market"] if order and order[0] != "SELL"]
    raise KeyError(component)


def farm_summary(farm):
    crops, animals, structures, cohorts = Counter(), Counter(), Counter(), Counter()
    critical_crops = 0
    for row in farm["tiles"]:
        for tile in row:
            if not isinstance(tile, dict):
                continue
            if tile.get("kind") == "PLANT":
                crops[tile["crop"]] += 1
                cohorts[f"{tile['crop']}:{tile.get('planted_day', -1)}"] += 1
                if not tile.get("watered_today") and tile.get("consecutive_unwatered", 0) >= 1:
                    critical_crops += 1
            elif tile.get("kind") in {"COOP", "PASTURE"}:
                structures[tile["kind"]] += 1
                if tile.get("animal"):
                    animals[tile["animal"]] += 1
    return {
        "money": float(farm["money"]),
        "farmer": list(farm["farmer"]),
        "hands": [list(value) for value in farm.get("hands", [])],
        "hand_count": len(farm.get("hands", [])),
        "hires_today": int(farm.get("hires_today", 0)),
        "quadrants": list(farm.get("unlocked_quadrants", [])),
        "crops": dict(sorted(crops.items())),
        "crop_cohorts": dict(sorted(cohorts.items())),
        "animals": dict(sorted(animals.items())),
        "structures": dict(sorted(structures.items())),
        "critical_crops": critical_crops,
    }


def state_anchor(replay, player, step):
    state = replay["steps"][step][player]
    obs = state["observation"]
    private = obs.get("private", {})
    return farm_summary(obs["farms"][player]) | {
        "step": step,
        "day": int(obs.get("day", step // 24)),
        "hour": int(obs.get("hour", step % 24)),
        "seeds": dict(private.get("seeds", {})),
        "shed": {key: value for key, value in private.get("shed", {}).items() if value},
        "inventories": [dict(inventory) for inventory in private.get("inventories", [])],
        "market_inventory": dict(obs["market"]["inventory"]),
        "market_prices": dict(obs["market"]["prices"]),
        "shops": list(obs["town"]["unlocked_shops"]),
    }


def fingerprint(appearance):
    payload = {
        "opening": [appearance["actions"][step] for step in range(0, 160)],
        "land": appearance["land_steps"],
        "animals": appearance["animal_trajectory"],
        "hands": appearance["hand_trajectory"],
        "phases": appearance["crop_phase_trajectory"],
        "non_sell": [action_component(action, "non_sell") for action in appearance["actions"]],
    }
    return hashlib.sha256(canonical(payload).encode()).hexdigest()


def load_appearances():
    manifest = json.loads((CORPUS / "manifest.json").read_text())
    players = {row["team_name"]: row for row in manifest["players"]}
    appearances = []
    for path in sorted((CORPUS / "replays").glob("episode-*-replay.json")):
        replay = json.loads(path.read_text())
        for player, name in enumerate(replay["info"]["TeamNames"]):
            if name not in players:
                continue
            actions = [normalized_action(replay, player, step) for step in range(719)]
            land_steps = []
            for step, action in enumerate(actions):
                if any(order and order[0] == "BUY_LAND" for order in action["market"]):
                    land_steps.append(step)
            checkpoints = [0, 24 * 4 + 23, 24 * 6 + 23, 24 * 8 + 23, 24 * 10 + 23, 24 * 15 + 23, 24 * 20 + 23, 24 * 25 + 23, 718]
            anchors = [state_anchor(replay, player, min(step, 718)) for step in checkpoints]
            row = {
                "team_name": name,
                "team_id": players[name]["team_id"],
                "submission_id": players[name]["submission_id"],
                "leaderboard_score": players[name]["leaderboard_score"],
                "episode_id": int(replay["info"]["EpisodeId"]),
                "player": player,
                "opponent": replay["info"]["TeamNames"][1 - player],
                "seed": int(replay["info"]["seed"]),
                "replay_path": str(path.relative_to(ROOT)),
                "final_money": float(replay["steps"][-1][player]["reward"]),
                "opponent_money": float(replay["steps"][-1][1 - player]["reward"]),
                "actions": actions,
                "anchors": anchors,
                "weed_dig_steps": [],
                "land_steps": land_steps,
                "hand_trajectory": [anchor["hand_count"] for anchor in anchors],
                "animal_trajectory": [anchor["animals"] for anchor in anchors],
                "crop_phase_trajectory": [anchor["crops"] for anchor in anchors],
            }
            for step, action in enumerate(actions):
                obs = replay["steps"][step][player]["observation"]
                farm = obs["farms"][player]
                positions = [farm["farmer"], *farm.get("hands", [])]
                field_actions = [action["farmer"], *action["hands"]]
                if any(
                    requested and requested[0] == "DIG"
                    and isinstance(farm["tiles"][position[1]][position[0]], dict)
                    and farm["tiles"][position[1]][position[0]].get("kind") == "WEED"
                    for position, requested in zip(positions, field_actions)
                ):
                    row["weed_dig_steps"].append(step)
            row["action_fingerprint"] = fingerprint(row)
            appearances.append(row)
    return manifest, appearances


def similarity(left, right, component="all", lo=0, hi=719):
    if component == "all":
        return sum(left["actions"][step] == right["actions"][step] for step in range(lo, hi)) / (hi - lo)
    return sum(
        action_component(left["actions"][step], component)
        == action_component(right["actions"][step], component)
        for step in range(lo, hi)
    ) / (hi - lo)


def stability(rows):
    components = ("farmer", "hands", "field", "market", "sell", "non_sell")
    output = {}
    for window, (lo, hi) in WINDOWS.items():
        by_component = {}
        for component in components:
            values = []
            unanimous = 0
            for step in range(lo, hi):
                counts = Counter(canonical(action_component(row["actions"][step], component)) for row in rows)
                mode = counts.most_common(1)[0][1]
                values.append(mode / len(rows))
                unanimous += mode == len(rows)
            by_component[component] = {
                "modal_stability": statistics.fmean(values),
                "unanimous_steps": unanimous,
                "steps": hi - lo,
            }
        output[window] = by_component
    return output


def classify_variation(rows, step):
    field = Counter(canonical(action_component(row["actions"][step], "field")) for row in rows)
    sell = Counter(canonical(action_component(row["actions"][step], "sell")) for row in rows)
    nonsell = Counter(canonical(action_component(row["actions"][step], "non_sell")) for row in rows)
    if len(field) == len(sell) == len(nonsell) == 1:
        return "stable"
    if len(field) == 1 and len(nonsell) == 1 and len(sell) > 1:
        return "market_dependent_sell"
    if len(field) == 1 and len(nonsell) > 1:
        return "market_dependent_non_sell"
    # A field difference that coincides with a weed at the acting source tile
    # is classified explicitly. Other field variation remains state-specific.
    weed = any(step in row["weed_dig_steps"] for row in rows)
    return "weed_repair" if weed else "environment_specific_field"


def cluster_submissions(grouped):
    names = sorted(grouped)
    # Submission similarity uses each submission's medoid. The 0.80 threshold
    # cleanly separates the four replay-supported architectures in this corpus.
    medoids = {}
    for submission, rows in grouped.items():
        medoids[submission] = max(
            rows,
            key=lambda row: sum(similarity(row, other) for other in rows),
        )
    parent = {name: name for name in names}

    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[b] = a

    pairwise = []
    for left, right in itertools.combinations(names, 2):
        score = similarity(medoids[left], medoids[right])
        pairwise.append({"left": left, "right": right, "all_action_similarity": score})
        if score >= 0.80:
            union(left, right)
    clusters = defaultdict(list)
    for name in names:
        clusters[find(name)].append(name)
    return list(clusters.values()), medoids, pairwise


def consensus_actions(rows, representative):
    actions, classification = [], []
    for step in range(719):
        kind = classify_variation(rows, step)
        classification.append(kind)
        output = {}
        for component in ("farmer", "hands", "market"):
            counts = Counter(canonical(row["actions"][step][component]) for row in rows)
            maximum = max(counts.values())
            choices = {value for value, count in counts.items() if count == maximum}
            preferred = canonical(representative["actions"][step][component])
            output[component] = json.loads(preferred if preferred in choices else sorted(choices)[0])
        actions.append(output)
    return actions, classification


def critical_transactions(actions):
    output = []
    for step, action in enumerate(actions):
        for index, order in enumerate(action["market"]):
            if not order or order[0] == "SELL":
                continue
            op = order[0]
            critical = op in {"BUY_LAND", "BUY_ANIMAL", "HIRE"}
            critical = critical or (op == "BUY_SEED" and int(order[2]) >= 5)
            critical = critical or (op == "BUY_PRODUCT" and order[1] == "WHEAT")
            if critical:
                output.append({
                    "step": step, "day": step // 24, "hour": step % 24,
                    "order_index": index, "order": order,
                    "maximum_delay": 8 if op != "HIRE" else min(8, 23 - step % 24),
                })
    return output


def main():
    source_manifest, appearances = load_appearances()
    grouped = defaultdict(list)
    for row in appearances:
        grouped[str(row["submission_id"])].append(row)
    clusters, medoids, pairwise = cluster_submissions(grouped)

    submission_rows = []
    for submission, rows in sorted(grouped.items()):
        variations = Counter(classify_variation(rows, step) for step in range(719))
        submission_rows.append({
            "submission_id": int(submission),
            "team_name": rows[0]["team_name"],
            "leaderboard_score": rows[0]["leaderboard_score"],
            "appearances": len(rows),
            "episode_ids": [row["episode_id"] for row in rows],
            "average_final_money": statistics.fmean(row["final_money"] for row in rows),
            "median_final_money": statistics.median(row["final_money"] for row in rows),
            "stability": stability(rows),
            "variation_classes": dict(variations),
            "medoid_episode": medoids[submission]["episode_id"],
        })

    route_bank = []
    for family_index, submissions in enumerate(sorted(clusters, key=lambda values: -max(grouped[value][0]["leaderboard_score"] for value in values)), 1):
        selected_submission = max(
            submissions,
            key=lambda value: statistics.fmean(row["final_money"] for row in grouped[value]),
        )
        rows = grouped[selected_submission]
        representative = medoids[selected_submission]
        consensus, classes = consensus_actions(rows, representative)
        representative_replay = json.loads((ROOT / representative["replay_path"]).read_text())
        route_id = f"v27_family_{family_index}_{representative['team_name'].lower().replace(' ', '_').replace('@', 'at').replace('.', '')}"
        route_bank.append({
            "route_id": route_id,
            "family_submissions": [int(value) for value in submissions],
            "family_teams": [grouped[value][0]["team_name"] for value in submissions],
            "selected_submission_id": int(selected_submission),
            "selected_team": representative["team_name"],
            "leaderboard_score_at_capture": representative["leaderboard_score"],
            "source_episode_id": representative["episode_id"],
            "source_player": representative["player"],
            "source_seed": representative["seed"],
            "source_replay_path": representative["replay_path"],
            "source_final_money": representative["final_money"],
            "source_opponent": representative["opponent"],
            "appearance_count": len(rows),
            "actions": representative["actions"],
            "consensus_actions": consensus,
            "variation_class_by_step": classes,
            "expected_state": [state_anchor(representative_replay, representative["player"], step) for step in range(719)],
            "critical_transactions": critical_transactions(representative["actions"]),
            "stability": stability(rows),
        })

    # Fixed split by entire route family. Extraction appearances characterize
    # routes; correction/evaluation opponents remain separate real submissions.
    split = {
        "extraction_route_families": [route["route_id"] for route in route_bank],
        "correction_development": ["Jayveer_melon_burst", "Lucas_four_quadrant"],
        "market_hazard_training": ["top corpus appearances excluding each tested source route"],
        "selection": ["Pedro_wheat_turnover", "Alexander_cow_melon", "Teddy_top_template", "Sagar_top_template"],
        "final_unseen": ["Prashant_crop_scaler", "David_four_quadrant", "Okome_strawberry_sheep", "Ayuma_crop_livestock", "Filip_top_template", "Amer_high_scale", "Yankang_wheat_close", "Garigariyong_strawberry"],
    }
    manifest = {
        "schema_version": 1,
        "source_manifest": "experiments/top_player_replays/manifest.json",
        "source_unique_replays": len(list((CORPUS / "replays").glob("episode-*-replay.json"))),
        "selected_appearances": len(appearances),
        "requested_action_indexing": "action for observation step s is replay.steps[s+1][player].action",
        "requested_actions": 719,
        "family_clustering": "connected components at >=0.80 full normalized-action similarity between submission medoids",
        "route_count": len(route_bank),
        "splits": split,
        "routes": route_bank,
    }
    stability_payload = {
        "schema_version": 1,
        "submission_count": len(grouped),
        "appearance_count": len(appearances),
        "submissions": submission_rows,
        "pairwise_submission_medoids": pairwise,
        "route_families": [
            {
                "route_id": route["route_id"],
                "submissions": route["family_submissions"],
                "teams": route["family_teams"],
                "selected_team": route["selected_team"],
                "source_episode_id": route["source_episode_id"],
            }
            for route in route_bank
        ],
    }
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2) + "\n")
    STABILITY_OUT.write_text(json.dumps(stability_payload, indent=2) + "\n")
    print(MANIFEST_OUT, f"{len(route_bank)} routes")
    print(STABILITY_OUT, f"{len(appearances)} appearances")


if __name__ == "__main__":
    main()
