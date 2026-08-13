"""O2: frozen routed best plus opponent-aware selling only."""

from runpy import run_path


common = run_path("agents/opponent_aware_common.py")
agent = common["make_agent"](selling=True)

