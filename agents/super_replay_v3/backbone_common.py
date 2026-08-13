"""Compact V3 research executor: selected elite route + exactly frozen K3."""

from pathlib import Path
from runpy import run_path
import json


ROOT = Path(__file__).resolve().parents[2]
V3_BANK = ROOT / "experiments/v3_route_executor.json"
_ROUTES = None


def _routes():
    global _ROUTES
    if _ROUTES is None:
        rows = json.loads(V3_BANK.read_text())["routes"]
        _ROUTES = {row["route_id"]: row for row in rows}
    return _ROUTES


def make_agent(route_id):
    route = _routes()[route_id]
    route = {**route, "critical_transactions": [],
             "variation_class_by_step": ["source_route"] * 719, "stability": {}}
    builder = run_path(str(ROOT / "agents/v27_backbone_common.py"))["make_v27_agent"]
    return builder(stage=3, route_override=route)
