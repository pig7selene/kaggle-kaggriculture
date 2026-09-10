"""Research-only V3 ablation: route 1 with the budget repair disabled."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_PATH = Path(__file__).with_name("main.py")
_SPEC = spec_from_file_location("public_farming_v3_force1_no_guard_base", _PATH)
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
_MODULE._select_route = lambda observation, seat: 1
_MODULE._budget_guard = lambda action, observation, route, step: action
agent = _MODULE.agent

