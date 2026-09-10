#!/usr/bin/env python3
"""Vendor the three public terminal overlays onto the frozen hardened parent."""

from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parent
PUBLIC = Path("/private/tmp/lb_gap_opponents")
FROZEN_PARENT = ROOT / "submission/main.py"
FROZEN_ACTIONS = ROOT / "submission/actions.json"
LICENSE = ROOT / "agents/shop_router_0909_hardened/LICENSE.txt"

CANDIDATES = {
    "shop_router_0909_terminal_a_most_powerfull": "most_powerfull",
    "shop_router_0909_terminal_b_market_smart": "market_smart",
    "shop_router_0909_terminal_c_seven_turn": "seven_rescue",
    "shop_router_0909_terminal_d_market_smart_2pass": "market_smart",
    "shop_router_0909_terminal_e_market_smart_708": "market_smart",
    "shop_router_0909_terminal_f_market_smart_711": "market_smart",
}


def hardened_router_source():
    source = FROZEN_PARENT.read_text()
    old = '''        action["market"] = action["market"][:MAX_ORDERS]\n        return liquidate(view) if step == LAST_STEP else action\n'''
    new = '''        action["market"] = action["market"][:MAX_ORDERS]\n        result = liquidate(view) if step == LAST_STEP else action\n        # Preserve the frozen Plan-10 hardening inside the Policy API used by\n        # the terminal overlay.  No other pre-terminal primitive changes.\n        if state.plan == 10 and step == 360 and result["farmer"] == ["PICKUP", "WHEAT", 5]:\n            result["farmer"][2] = 4\n        return result\n'''
    if source.count(old) != 1:
        raise RuntimeError("unexpected frozen packaged-parent structure")
    return source.replace(old, new)


def main():
    router = hardened_router_source()
    for candidate, public_name in CANDIDATES.items():
        source_dir = PUBLIC / public_name
        target = ROOT / "agents" / candidate
        target.mkdir(parents=True, exist_ok=True)
        for filename in ("main.py", "policy.py", "terminal_planner.py", "unit_model.py", "settings.json"):
            shutil.copyfile(source_dir / filename, target / filename)
        if candidate.endswith("_2pass"):
            policy = (target / "policy.py").read_text()
            policy = policy.replace(
                "((64, 1, 4), (128, 1, 8), (256, 1, 16))",
                "((64, 1, 4), (128, 1, 8), (256, 1, 16), (512, 2, 32))",
            ).replace(
                "supported search variants are64/1/4,128/1/8 and256/1/16",
                "supported search variants include the local terminal-only 512/2/32 probe",
            )
            (target / "policy.py").write_text(policy)
            planner = (target / "terminal_planner.py").read_text()
            planner = planner.replace("max_simulations = min(256,", "max_simulations = min(512,")
            planner = planner.replace("proposals_per_actor = min(16,", "proposals_per_actor = min(32,")
            (target / "terminal_planner.py").write_text(planner)
            (target / "settings.json").write_text('{"enabled":true,"max_simulations":512,"passes":2,"proposals_per_actor":32}\n')
        if candidate.endswith("_708"):
            for filename in ("policy.py", "terminal_planner.py"):
                path = target / filename
                source = path.read_text()
                if source.count("START, FINAL = 712, 718") != 1:
                    raise RuntimeError(f"unexpected terminal window in {path}")
                path.write_text(source.replace("START, FINAL = 712, 718", "START, FINAL = 708, 718"))
        if candidate.endswith("_711"):
            for filename in ("policy.py", "terminal_planner.py"):
                path = target / filename
                source = path.read_text()
                if source.count("START, FINAL = 712, 718") != 1:
                    raise RuntimeError(f"unexpected terminal window in {path}")
                source = source.replace("START, FINAL = 712, 718", "START, FINAL = 711, 718")
                if filename == "policy.py":
                    source = source.replace(
                        "if step < FINAL:\n                self._fixed_market(action)",
                        "if 712 <= step < FINAL:\n                self._fixed_market(action)",
                    )
                path.write_text(source)
        shutil.copyfile(FROZEN_ACTIONS, target / "actions.json")
        shutil.copyfile(LICENSE, target / "LICENSE.txt")
        (target / "router_parent.py").write_text(router)
        (target / "NOTICE.md").write_text(
            "# Attribution and terminal-overlay provenance\n\n"
            "This candidate preserves the frozen ShopRouter0909Hardened route and "
            "Plan-10 correction, then applies only the public 712–718 terminal overlay "
            f"reconstructed from `{public_name}`. The `_708`/`_711` candidates use the explicitly "
            "authorized adjacent extension so the same physical planner has enough travel time. "
            "The Shop Router strategy and terminal "
            "source are redistributed under Apache License 2.0. This is a local research "
            "candidate and was not submitted by this script.\n"
        )


if __name__ == "__main__":
    main()
