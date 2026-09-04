"""S1: CurrentBest plus persistent worker territories."""

from runpy import run_path

agent = run_path("agents/territory_lifecycle_common.py")["make_agent"]("S1")

