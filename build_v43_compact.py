"""Merge the sell queue, as V48 does and the alperen chassis does not.

The two strongest public builds are different forks: alperen5252525's "Ready
Stock, Earlier Sales" beats V48 by +362, and V48 carries a queue compaction its
author measured at +226 over V47 which alperen has no equivalent of -- 169
function definitions against alperen's 149, and no `_e334_compact`.

Within a contiguous run of sell orders for the cash goods, the routine sums
repeated orders of the same product, clamps each to the stock that will actually
exist after this step's unit actions, keeps first-appearance order, and leaves
the freed slots empty rather than pulling later orders forward. That ordering is
the point: the engine fills slot by slot against a shared book, so two milk
orders in slots three and five sell part of the lot after the book has already
moved, while one merged order in slot three takes the whole lot at the better
price. Leaving holes keeps every purchase and hire on the index the rest of the
chassis expects.

Ported verbatim in behaviour and placed last, so it also merges the orders our
own lead layer appends.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- sell-queue compaction
_QC_CFG = @@CFG@@
_QC_ITEMS = set(_QC_CFG["items"])
_QC_PARENT = agent
_QC_TELEMETRY = {"steps": 0, "changed": 0, "removed": 0, "merged_units": 0, "errors": 0}


def _qc_compact(obs, action):
    market = action.get("market") or []
    if int(obs["step"]) < _QC_CFG["from_step"] or len(market) < 2:
        return action
    segments = []
    i = 0
    while i < len(market):
        o = market[i]
        if len(o) >= 3 and o[0] == "SELL" and o[1] in _QC_ITEMS:
            j = i + 1
            while j < len(market) and len(market[j]) >= 3 and market[j][0] == "SELL" and market[j][1] in _QC_ITEMS:
                j += 1
            if j - i >= 2:
                segments.append((i, j))
            i = j
        else:
            i += 1
    if not segments:
        return action
    _, private = _r127_fields(obs, action)
    remaining = dict(private["shed"])
    new = [list(o) for o in market]
    removed = 0
    merged = 0
    for start, end in segments:
        quantities = {}
        order = []
        for o in market[start:end]:
            p = o[1]
            if p not in quantities:
                order.append(p)
                quantities[p] = 0
            quantities[p] += max(0, int(o[2]))
        kept = []
        for p in order:
            q = min(quantities[p], max(0, int(remaining.get(p, 0))))
            if q:
                kept.append(["SELL", p, q])
                remaining[p] -= q
                merged += q
        # empty slots are skipped by the engine; holes keep every later
        # purchase and hire on the index the rest of the chassis expects
        replacement = kept + [[] for _ in range(end - start - len(kept))]
        if replacement != market[start:end]:
            removed += end - start - len(kept)
            new[start:end] = replacement
    if new == market:
        return action
    _QC_TELEMETRY["changed"] += 1
    _QC_TELEMETRY["removed"] += removed
    _QC_TELEMETRY["merged_units"] += merged
    return dict(action, market=new)


def agent(observation, configuration=None):
    action = _QC_PARENT(observation, configuration)
    try:
        _QC_TELEMETRY["steps"] += 1
        return _qc_compact(observation, action)
    except Exception:
        _QC_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_QC_PARENT, "telemetry", {}) or {}), "queue_compact": _QC_TELEMETRY}
kaggle_agent = agent
'''

CASH = ("CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL")
ALL = CASH + ("WHEAT", "FERTILIZER")
VARIANTS = {
    "qc": {"from_step": 144, "items": CASH},
    "qc_all": {"from_step": 144, "items": ALL},
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="alp_dw_46_fv_r30")
    a = ap.parse_args()
    src = (VD / f"{a.base}.py").read_text().rstrip()
    if "_r127_fields" not in src:
        raise SystemExit(f"{a.base} has no _r127_fields to project the shed with")
    receipt = {}
    for name, cfg in VARIANTS.items():
        out = VD / f"{a.base}_{name}.py"
        out.write_text(src + "\n" + WRAPPER.replace("@@CFG@@", repr(cfg)))
        receipt[out.stem] = {"base": a.base, "cfg": cfg, "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print("built", out.name)
    (ROOT / "experiments" / "v43_compact_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
