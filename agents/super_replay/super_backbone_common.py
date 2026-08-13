"""Research wrapper: arbitrary elite route + the frozen K3 correction layer."""

from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
EXECUTOR_BANK = ROOT / "experiments/super_replay_route_executor.json"


def make_super_agent(route_id):
    bank_path = EXECUTOR_BANK if EXECUTOR_BANK.is_file() else ROOT / "experiments/super_replay_route_bank.json"
    bank = __import__("json").loads(bank_path.read_text())
    route = next((value for value in bank["routes"] if value["route_id"] == route_id), None)
    if route is None and bank_path == EXECUTOR_BANK:
        bank = __import__("json").loads((ROOT / "experiments/super_replay_route_bank.json").read_text())
        route = next((value for value in bank["routes"] if value["route_id"] == route_id), None)
    if route is None:
        raise KeyError(route_id)
    route = {
        **route,
        "critical_transactions": [],
        "variation_class_by_step": ["source_route"] * 719,
        "stability": {},
    }
    builder = run_path(str(ROOT / "agents/v27_backbone_common.py"))["make_v27_agent"]
    return builder(stage=3, route_override=route)
