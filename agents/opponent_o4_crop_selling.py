"""O4: frozen routed best plus crop and selling opponent awareness."""

from runpy import run_path


common = run_path("agents/opponent_aware_common.py")
agent = common["make_agent"](crop=True, selling=True)

