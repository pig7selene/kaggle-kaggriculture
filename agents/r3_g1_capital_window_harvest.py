"""THIS GUARD IS INTENDED TO FIX: cash arriving after a critical investment window.

The diagnosis found no qualifying pre-third-deed event, so this conservative
control is intentionally action-equivalent to frozen R3.  It documents that
the proposed capital-window exception is not admitted without evidence.
"""

from runpy import run_path


agent = run_path("agents/r3_guard_common.py")["make_guard"]()
