"""O1: frozen routed best plus opponent-aware crop scoring only."""

from runpy import run_path


common = run_path("agents/opponent_aware_common.py")
agent = common["make_agent"](crop=True)

