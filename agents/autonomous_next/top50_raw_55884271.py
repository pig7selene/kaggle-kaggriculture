"""Complete Top-50 raw replay route from the highest-money mined episode."""

from pathlib import Path
from runpy import run_path


ROOT = Path(__file__).resolve().parents[2]
agent = run_path(str(ROOT / "agents/top50_distilled/backbone_common.py"))["make_agent"]("super_raw_55884271")
