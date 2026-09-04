"""Complete Top-50 replay route with frozen bounded K3 repair."""

from runpy import run_path

agent = run_path("agents/top50_distilled/backbone_common.py")["make_agent"]('super_raw_55886665')
