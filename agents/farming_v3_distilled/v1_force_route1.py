"""Candidate V1: exact public V3 policy with the turn-360 branch fixed to route 1.

This is a research candidate, not a deployment file.  It deliberately reuses the
hash-verified public source so the only behavioral change is the route selector.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_PATH = Path(__file__).parents[1] / "public_farming_v3" / "main.py"
_SPEC = spec_from_file_location("farming_v3_distilled_v1_base", _PATH)
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
_MODULE._select_route = lambda observation, seat: 1
agent = _MODULE.agent

