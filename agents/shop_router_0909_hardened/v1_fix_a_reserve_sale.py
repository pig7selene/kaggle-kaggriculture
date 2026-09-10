"""Plan-10 Fix A: sell eight rather than nine wheat at step 332."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("shop0909_hardening_common_a", Path(__file__).with_name("common.py"))
_common = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_common)
agent = _common.make_agent("reserve_sale")
