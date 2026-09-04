"""Complete-route challenger selected by the fresh route-bank oracle.

The route is executed whole through the existing bounded Stage-3 repair; no
actions are spliced into the frozen portfolio.
"""

from runpy import run_path

agent = run_path("agents/top50_distilled/backbone_common.py")["make_agent"]("super_raw_55885628")

