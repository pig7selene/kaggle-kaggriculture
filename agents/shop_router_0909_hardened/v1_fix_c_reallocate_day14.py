"""Plan-10 Fix C: give one day-14 pickup unit to the final feeder."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("shop0909_hardening_common_c", Path(__file__).with_name("common.py"))
_common = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_common)
agent = _common.make_agent("reallocate_day14")
