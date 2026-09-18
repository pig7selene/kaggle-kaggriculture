"""Do not race a rival who is already building the same herd.

The rival's whole farm is public. Our chassis, like every public build, decides
its sheep expansion from the town alone: two yarn stores and it buys land, six
sheep and two hands. In our own online games that gamble pays when the rival
does not take it -- nineteen sheep against their eleven kept wool at $247 and
won by 18,944 and 30,649 -- and fails badly when they do: nineteen against
fifteen crashed wool to $66 and lost 15,405, with 4,000 more spent on land and
4,400 more on hands than the winner.

Wool only holds its price while demand outruns supply, so the expansion is
worth capital exactly when we are the only one making it. This layer reads the
rival's visible sheep and pastures at the moment the chassis commits and drops
the land purchase and the bulk sheep order when they are already committed,
keeping the money instead.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- rival guard
_RG_CFG = @@CFG@@
_RG_PARENT = agent
_RG_STATE = {}
_RG_TELEMETRY = {"steps": 0, "land_blocked": 0, "sheep_blocked": 0, "hires_blocked": 0,
                 "let_through": 0, "errors": 0, "last": ""}


def _rg_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def _rg_herd(farm):
    sheep = pasture = cows = 0
    for row in (_rg_get(farm, "tiles") or []):
        for t in row:
            if not isinstance(t, dict):
                continue
            a = t.get("animal")
            if a == "SHEEP":
                sheep += 1
            elif a == "COW":
                cows += 1
            elif t.get("kind") == "PASTURE":
                pasture += 1
    return sheep, pasture, cows


def agent(observation, configuration=None):
    action = _RG_PARENT(observation, configuration)
    try:
        _RG_TELEMETRY["steps"] += 1
        step = int(_rg_get(observation, "step", -1))
        seat = int(_rg_get(observation, "player", 0) or 0)
        if step == 0:
            _RG_STATE.pop(seat, None)
        if step < _RG_CFG["from_step"] or step > _RG_CFG["to_step"]:
            return action
        market = [list(o) for o in (action.get("market") or []) if o]
        farms = list(_rg_get(observation, "farms", []) or [])
        if len(farms) < 2:
            return action
        quads = len(list(_rg_get(farms[seat], "unlocked_quadrants", []) or []))
        big = [o for o in market if o[0] == "BUY_ANIMAL" and len(o) >= 3 and o[1] == "SHEEP"
               and int(o[2]) >= _RG_CFG["bulk"]]
        # the tape buys its two quadrants at steps 150 and 265; a purchase while we
        # already hold three is the conditional sheep expansion, and only that one
        # is the gamble worth declining
        land = [o for o in market if o[0] == "BUY_LAND"] if quads >= _RG_CFG["min_quads"] else []
        if not big and not land:
            return action
        r_sheep, r_pasture, _ = _rg_herd(farms[1 - seat])
        o_sheep, o_pasture, _ = _rg_herd(farms[seat])
        st = _RG_STATE.setdefault(seat, {"blocked": False})
        # their committed capacity: sheep already placed plus pastures waiting
        rival_capacity = r_sheep + r_pasture
        contested = rival_capacity >= _RG_CFG["rival_capacity"] or r_sheep >= _RG_CFG["rival_sheep"]
        _RG_TELEMETRY["last"] = f"step {step} ours {o_sheep}+{o_pasture} rival {r_sheep}+{r_pasture}"
        if not contested:
            _RG_TELEMETRY["let_through"] += 1
            return action
        st["blocked"] = True
        keep = []
        for o in market:
            if o[0] == "BUY_LAND" and _RG_CFG["block_land"] and quads >= _RG_CFG["min_quads"]:
                _RG_TELEMETRY["land_blocked"] += 1
                continue
            if o[0] == "BUY_ANIMAL" and len(o) >= 3 and o[1] == "SHEEP" and int(o[2]) >= _RG_CFG["bulk"]:
                _RG_TELEMETRY["sheep_blocked"] += int(o[2])
                continue
            if o[0] == "HIRE" and _RG_CFG["block_hires"] and st.get("blocked"):
                _RG_TELEMETRY["hires_blocked"] += 1
                continue
            keep.append(o)
        action["market"] = keep
        return action
    except Exception:
        _RG_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_RG_PARENT, "telemetry", {}) or {}), "rival_guard": _RG_TELEMETRY}
kaggle_agent = agent
'''

DEFAULTS = {"from_step": 280, "to_step": 460, "bulk": 4, "rival_capacity": 14, "rival_sheep": 9,
            "min_quads": 3, "block_land": True, "block_hires": False}
VARIANTS = {
    "rg_c14": dict(DEFAULTS),
    "rg_c12": {**DEFAULTS, "rival_capacity": 12, "rival_sheep": 8},
    "rg_c16": {**DEFAULTS, "rival_capacity": 16, "rival_sheep": 10},
    "rg_c14_noland": {**DEFAULTS, "block_land": False},
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="alp_dw_46_fv_r30")
    a = ap.parse_args()
    src = (VD / f"{a.base}.py").read_text().rstrip()
    receipt = {}
    for name, cfg in VARIANTS.items():
        out = VD / f"{a.base}_{name}.py"
        out.write_text(src + "\n" + WRAPPER.replace("@@CFG@@", repr(cfg)))
        receipt[out.stem] = {"base": a.base, "cfg": cfg, "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print("built", out.name)
    (ROOT / "experiments" / "v43_rival_guard_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
