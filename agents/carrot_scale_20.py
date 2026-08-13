"""Twenty carrot plots with four hired hands per day."""

from pathlib import Path
from runpy import run_path

_make_agent = run_path(str(Path(__file__).with_name("carrot_scale_common.py")))[
    "make_agent"
]
_agent = _make_agent(20)


def agent(obs):
    return _agent(obs)

