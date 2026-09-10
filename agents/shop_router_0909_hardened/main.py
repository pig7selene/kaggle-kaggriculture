"""Locked Plan-10 hardening of Yusuke Hayashi's public Shop Router 0909.

The exact Apache-2.0 parent remains under ``agents/shop_router_0909``.  This
candidate changes one primitive only while Plan 10 is active: at step 360 the
main farmer picks up four wheat instead of five.  The released unit remains in
the shed for the final animal-service worker, preventing the deterministic
Yarn Store -> Pet Cafe sheep escape without shifting the action tape.
"""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("shop0909_hardening_common_final", Path(__file__).with_name("common.py"))
_common = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_common)
agent = _common.make_agent("reallocate_day15")
