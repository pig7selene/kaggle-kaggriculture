"""Compact V2 research executor: elite route + frozen K3 worker weed repair."""

from pathlib import Path
from runpy import run_path
import json


ROOT = Path(__file__).resolve().parents[2]
V2_BANK = ROOT / "experiments/v2_route_executor.json"
V1_BANK = ROOT / "experiments/super_replay_route_executor.json"
_ROUTES = None


def _routes():
    global _ROUTES
    if _ROUTES is None:
        rows = json.loads(V2_BANK.read_text())["routes"]
        rows.extend(json.loads(V1_BANK.read_text())["routes"])
        _ROUTES = {row["route_id"]: row for row in rows}
    return _ROUTES


def make_agent(route_id):
    route = _routes()[route_id]
    route = {**route, "critical_transactions": [], "variation_class_by_step": ["source_route"] * 719, "stability": {}}
    builder = run_path(str(ROOT / "agents/v27_backbone_common.py"))["make_v27_agent"]
    return builder(stage=3, route_override=route)
