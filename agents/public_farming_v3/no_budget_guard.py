"""Research-only V3 ablation: retain route selection but disable budget repair."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


_PATH = Path(__file__).with_name("main.py")
_SPEC = spec_from_file_location("public_farming_v3_no_guard_base", _PATH)
_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
_MODULE._budget_guard = lambda action, observation, route, step: action
agent = _MODULE.agent

