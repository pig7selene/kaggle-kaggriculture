"""Lead the lots the town actually pays for, not a fixed four.

The five-step lead sells the tape's future premium lots early and is worth
+1,946 against shipped, but its item list is frozen at wool, milk, strawberry
and melon. What a town pays for varies enormously -- shipped's money by first
two shops runs 49k to 177k -- and racing a clone for a $1 item wins nothing
while conceding a scarce one costs real money. In a pet-cafe town the scarce
good is carrot, and the online engine prices a short carrot or tomato on a
quadratic hinge the local build does not have: 500 carrots short is $77 online
against $42 locally.

Two selection rules are offered. The price rule leads anything above a
threshold plus the premium four. The impact rule computes what the race is
actually worth -- this lot's revenue now minus its revenue after an identical
clone lot lands first, under the online curves -- and leads when that exceeds a
floor. Neither adds supply: only lots the tape is about to sell are moved.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")
WRAPPER = Path("/private/tmp/claude-501/-Users-infiniteejl-Projects-kaggriculture/f8b95bd4-a052-4177-b544-60e3c44ceeac/scratchpad/dl_wrapper.txt").read_text()

PREM = ("WOOL", "MILK", "STRAWBERRY", "MELON")
ALL = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
DEFAULTS = {"lookahead": 5, "min_price": 2, "min_ratio": 0.0, "top_k": 0, "always": (), "min_impact": 0.0,
            "window_lo": 0, "window_hi": 0}
VARIANTS = {
    "dl_g50": {**DEFAULTS, "min_price": 50, "always": PREM},
    "di_100": {**DEFAULTS, "always": ALL, "min_impact": 100.0},
    "di_200": {**DEFAULTS, "always": ALL, "min_impact": 200.0},
    "di_400": {**DEFAULTS, "always": ALL, "min_impact": 400.0},
    "di_800": {**DEFAULTS, "always": ALL, "min_impact": 800.0},
    "di_g50_200": {**DEFAULTS, "min_price": 50, "always": PREM, "min_impact": 200.0},
    "dw_46": {**DEFAULTS, "min_price": 50, "always": PREM, "window_lo": 4, "window_hi": 6},
    "dw_38": {**DEFAULTS, "min_price": 50, "always": PREM, "window_lo": 3, "window_hi": 8},
    "dw_57": {**DEFAULTS, "min_price": 50, "always": PREM, "window_lo": 5, "window_hi": 7},
    "dw_510": {**DEFAULTS, "min_price": 50, "always": PREM, "window_lo": 5, "window_hi": 10},
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="room_plus_clamp", help="base WITHOUT a lead layer")
    ap.add_argument("--only", help="comma-separated variant names")
    a = ap.parse_args()
    src = (VD / f"{a.base}.py").read_text().rstrip()
    if "_PL_PARENT" in src or "_DL_PARENT" in src:
        raise SystemExit(f"{a.base} already carries a lead layer; use room_plus_clamp")
    want = set(a.only.split(",")) if a.only else set(VARIANTS)
    receipt = {}
    for name, cfg in VARIANTS.items():
        if name not in want:
            continue
        out = VD / f"{name}.py"
        out.write_text(src + "\n" + WRAPPER.replace("@@CFG@@", repr(cfg)))
        receipt[name] = {"base": a.base, "cfg": cfg, "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print("built", out.name)
    (ROOT / "experiments" / "v43_dynamic_lead_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
