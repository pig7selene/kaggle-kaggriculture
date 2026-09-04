"""Route-family challenger used to falsify the fixed three-parent selector."""

from runpy import run_path


agent = run_path("agents/top50_distilled/backbone_common.py")["make_agent"](
    "super_family_01_medoid"
)
