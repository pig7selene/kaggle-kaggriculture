"""High-money raw Top-50 route used as a route-selection control."""

from runpy import run_path


agent = run_path("agents/top50_distilled/backbone_common.py")["make_agent"](
    "super_raw_55899537"
)
