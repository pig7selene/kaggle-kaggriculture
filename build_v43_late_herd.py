"""Choose the herd when the town is known, not at step 196.

Every team above 92k ends a yarn-free town with no sheep and a yarn-rich one
with four to eleven; our chassis buys six either way, at steps 196 to 226, when
three of the eight shops have opened. The information to choose does not exist
then -- but it does by day 12, and the chassis already carries the machinery to
act on it: `_v233` buys the fourth quadrant, six sheep and two hands at day 12
and drives those hands to place the animals, gated on two yarn stores and wool
at 220.

So the herd decision splits in two. Early, take the broad bet: a cow costs 400
against a sheep's 500 and milk is bought by three shop types where wool is
bought by one, so cows are the better purchase under ignorance. Late, once the
town has shown itself, let the existing expansion add sheep back where wool is
actually worth something. Swapping early without the late half is what lost
6,890 in a three-yarn town; the two halves belong together.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

# the chassis's own late-expansion gate, and looser versions of it
GATE_OLD = "obs['town']['unlocked_shops'].count('YARN_STORE')<2 or prices['WOOL']<220"
GATES = {
    "y2w220": GATE_OLD,
    "y1w150": "obs['town']['unlocked_shops'].count('YARN_STORE')<1 or prices['WOOL']<150",
    "y1w180": "obs['town']['unlocked_shops'].count('YARN_STORE')<1 or prices['WOOL']<180",
    "y2w180": "obs['town']['unlocked_shops'].count('YARN_STORE')<2 or prices['WOOL']<180",
}

WRAPPER = '''

# ---------------------------------------------------------------- early cows
_EC_CFG = @@CFG@@
_EC_PARENT = agent
_EC_STATE = {}
_EC_TELEMETRY = {"steps": 0, "bought_cows": 0, "placed": 0, "picked": 0, "errors": 0}


def _ec_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def agent(observation, configuration=None):
    action = _EC_PARENT(observation, configuration)
    try:
        _EC_TELEMETRY["steps"] += 1
        step = int(_ec_get(observation, "step", -1))
        seat = int(_ec_get(observation, "player", 0) or 0)
        if step == 0:
            _EC_STATE.pop(seat, None)
        if not (_EC_CFG["from_step"] <= step <= _EC_CFG["to_step"]):
            return action
        private = _ec_get(observation, "private", {}) or {}
        shed = dict(_ec_get(private, "shed", {}) or {})
        st = _EC_STATE.setdefault(seat, {"swapped": 0})
        market = []
        for o in (action.get("market") or []):
            if not o:
                continue
            o = list(o)
            if o[0] == "BUY_ANIMAL" and len(o) >= 3 and o[1] == "SHEEP":
                n = max(0, int(o[2]))
                o = ["BUY_ANIMAL", "COW", n]
                st["swapped"] += n
                _EC_TELEMETRY["bought_cows"] += n
            market.append(o)
        action["market"] = market
        if st["swapped"] > 0:
            units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
            have_sheep = int(shed.get("SHEEP", 0) or 0)
            for i, u in enumerate(units):
                if u and u[0] in ("PICKUP", "PLACE") and len(u) >= 2 and u[1] == "SHEEP" and have_sheep <= 0:
                    units[i] = [u[0], "COW"] + list(u[2:])
                    _EC_TELEMETRY["placed" if u[0] == "PLACE" else "picked"] += 1
            action["farmer"] = units[0]
            action["hands"] = units[1:]
        return action
    except Exception:
        _EC_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_EC_PARENT, "telemetry", {}) or {}), "early_cows": _EC_TELEMETRY}
kaggle_agent = agent
'''

DEFAULTS = {"from_step": 150, "to_step": 280}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="alp_dw_46_fv_r30")
    a = ap.parse_args()
    src = (VD / f"{a.base}.py").read_text()
    if src.count(GATE_OLD) != 1:
        raise SystemExit(f"expected exactly one late-expansion gate, found {src.count(GATE_OLD)}")
    receipt = {}
    for gname, gate in GATES.items():
        for early in (False, True):
            name = f"{a.base}_lh_{gname}" + ("_cows" if early else "")
            s = src.replace(GATE_OLD, gate)
            if early:
                s = s.rstrip() + "\n" + WRAPPER.replace("@@CFG@@", repr(DEFAULTS))
            out = VD / f"{name}.py"
            out.write_text(s)
            receipt[name] = {"base": a.base, "gate": gate, "early_cows": early,
                             "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
            print("built", out.name)
    (ROOT / "experiments" / "v43_late_herd_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
