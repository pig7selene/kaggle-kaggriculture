"""Executor for current Top-3 public medoid-route reconstructions."""

from pathlib import Path
from runpy import run_path
import json


ROOT = Path(__file__).resolve().parents[2]
_ROUTES = None


def _routes():
    global _ROUTES
    if _ROUTES is None:
        rows = json.loads((ROOT / "experiments/top3_raw_route_bank.json").read_text())["routes"]
        _ROUTES = {row["route_id"]: row for row in rows}
    return _ROUTES


def make_agent(route_id):
    route = {
        **_routes()[route_id],
        "critical_transactions": [],
        "variation_class_by_step": ["public_medoid_route"] * 719,
        "stability": {},
    }
    builder = run_path(str(ROOT / "agents/v27_backbone_common.py"))["make_v27_agent"]
    return builder(stage=3, route_override=route)
