"""Candidate A: Dmitry complete economy with bounded livestock safety."""

from runpy import run_path

agent = run_path("agents/top50_distilled/safety_common.py")["make_safe"](
    "agents/top50_distilled/raw/super_raw_55859516.py",
    exact_rescues=((686, 2, 4),),
)
