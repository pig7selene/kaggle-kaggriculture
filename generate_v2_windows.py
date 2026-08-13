"""Generate a few elite-supported low-confidence SELL-window replacements."""

from copy import deepcopy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
V1_BANK = ROOT / "experiments/super_replay_route_bank.json"
V2_BANK = ROOT / "experiments/v2_route_bank.json"
EXECUTOR = ROOT / "experiments/v2_route_executor.json"
INDEX = ROOT / "agents/super_replay_v2/index.json"
OUT = ROOT / "agents/super_replay_v2"
WINDOW_OUT = ROOT / "experiments/v2_window_candidates.json"

# Each window is centered on stable JALKARNA sale events where the two routes'
# field actions are identical.  Only market orders are replaced.
WINDOWS = {
    "v2_window_jalkarna_wool356": (348, 361),
    "v2_window_jalkarna_wool375": (367, 384),
    "v2_window_jalkarna_milk431": (424, 439),
    "v2_window_jalkarna_milk455": (448, 463),
    "v2_window_jalkarna_premium502": (496, 505),
    "v2_window_jalkarna_mid_all": (348, 505),
}


def main():
    v1 = next(row for row in json.loads(V1_BANK.read_text())["routes"] if row["route_id"] == "super_raw_55459817")
    donor = next(row for row in json.loads(V2_BANK.read_text())["routes"] if row["route_id"] == "super_raw_55463387")
    executor = json.loads(EXECUTOR.read_text()); index = json.loads(INDEX.read_text())
    existing = {row["route_id"] for row in executor["routes"]}; audit = []
    for name, (lo, hi) in WINDOWS.items():
        actions = deepcopy(v1["consensus_actions"])
        changed = []
        for step in range(lo, hi):
            if actions[step]["market"] != donor["consensus_actions"][step]["market"]:
                actions[step]["market"] = deepcopy(donor["consensus_actions"][step]["market"]); changed.append(step)
        route_id = name.removeprefix("v2_")
        route = {
            "route_id": route_id, "family_id": "v2_low_confidence_market_window",
            "source_team": "Ricardo field + JALKARNA market window", "source_submission_id": donor["source_submission_id"],
            "source_episode_id": donor["source_episode_id"], "source_player": donor["source_player"],
            "source_seed": donor["source_seed"], "source_replay_path": donor["source_replay_path"],
            "consensus_actions": actions, "expected_state": deepcopy(v1["expected_state"]),
            "milestones": v1.get("milestones", {}),
            "window": {"start": lo, "end": hi, "changed_market_steps": changed},
        }
        if route_id not in existing: executor["routes"].append(route); existing.add(route_id)
        path = OUT / f"{name}.py"
        path.write_text('"""Elite-supported bounded market-window route replacement."""\n\nfrom runpy import run_path\n\n' + f'agent = run_path("agents/super_replay_v2/backbone_common.py")["make_agent"]({route_id!r})\n')
        index[name] = str(path.relative_to(ROOT)); audit.append({"name": name, **route["window"]})
    executor["route_count"] = len(executor["routes"])
    EXECUTOR.write_text(json.dumps(executor, separators=(",", ":")) + "\n")
    INDEX.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    WINDOW_OUT.write_text(json.dumps({"schema_version": 1, "candidates": audit}, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__": main()
