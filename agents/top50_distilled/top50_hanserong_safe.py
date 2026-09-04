"""Candidate B: Hanserong complete economy with bounded livestock safety."""

from runpy import run_path

agent = run_path("agents/top50_distilled/safety_common.py")["make_safe"](
    "agents/top50_distilled/raw/super_raw_55886665.py",
    exact_rescues=((25, 4, 4),),
)
