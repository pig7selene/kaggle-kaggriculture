"""S0 control: exact frozen Top-50 CurrentBest."""

from runpy import run_path

agent = run_path("agents/territory_lifecycle_common.py")["make_agent"]("S0")

