"""Second complete-route oracle challenger (control route)."""

from runpy import run_path

agent = run_path("agents/top50_distilled/backbone_common.py")["make_agent"]("super_raw_55909034")

