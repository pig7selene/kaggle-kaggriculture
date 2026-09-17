"""Feed cows and geese every other day, as the strong forks do.

All four high-scoring V43 forks feed 28-55 fewer times a game than the tape.
An animal only escapes after two consecutive unfed days, its base yield accrues
whether fed or not, and feeding buys only the care bonus: one extra unit on a
production day, provided the animal was also cared for. For a cow or goose that
unit is $26-42 of glutted milk or egg; the feed costs a wheat ($35-39 in a
typical game) and a unit-step. Sheep are different -- wool is pinned at its
$241 ceiling whenever a yarn store exists -- so they keep the tape's feeding.

The layer turns FEED into PASS on a cow or goose that was fed yesterday
(consecutive_unfed == 0), and optionally the matching CARE, which is worthless
without the feed. The saved wheat stays in the unit's inventory and reaches the
shed with everything else.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

WRAPPER = '''

# ---------------------------------------------------------------- feed less
_FL_CFG = @@CFG@@
_FL_PARENT = agent
_FL_TELEMETRY = {"steps": 0, "feeds_skipped": 0, "cares_skipped": 0, "errors": 0}


def _fl_get(o, k, d=None):
    return o.get(k, d) if isinstance(o, dict) else getattr(o, k, d)


def agent(observation, configuration=None):
    action = _FL_PARENT(observation, configuration)
    try:
        _FL_TELEMETRY["steps"] += 1
        step = int(_fl_get(observation, "step", -1))
        if step < _FL_CFG["from_step"]:
            return action
        seat = int(_fl_get(observation, "player", 0) or 0)
        farm = _fl_get(observation, "farms", [])[seat]
        tiles = _fl_get(farm, "tiles")
        positions = [_fl_get(farm, "farmer")] + [list(p) for p in (_fl_get(farm, "hands", []) or [])]
        units = [action.get("farmer") or ["PASS"]] + list(action.get("hands") or [])
        for i in range(min(len(units), len(positions))):
            u = units[i]
            if not u or u[0] not in ("FEED", "CARE"):
                continue
            pos = positions[i]
            if not isinstance(pos, (list, tuple)):
                continue
            tile = tiles[int(pos[1])][int(pos[0])]
            if not isinstance(tile, dict) or tile.get("animal") not in _FL_CFG["animals"]:
                continue
            # skip only when yesterday was fed: one unfed day is safe, two lose the animal
            if int(tile.get("consecutive_unfed", 0) or 0) != 0:
                continue
            if tile.get("fed_today"):
                continue
            if u[0] == "FEED":
                units[i] = ["PASS"]
                _FL_TELEMETRY["feeds_skipped"] += 1
            elif _FL_CFG["skip_care"]:
                units[i] = ["PASS"]
                _FL_TELEMETRY["cares_skipped"] += 1
        action["farmer"] = units[0]
        action["hands"] = units[1:]
        return action
    except Exception:
        _FL_TELEMETRY["errors"] += 1
        return action


agent.telemetry = {**(getattr(_FL_PARENT, "telemetry", {}) or {}), "feed_less": _FL_TELEMETRY}
kaggle_agent = agent
'''

VARIANTS = {
    "fl_cowgoose": {"animals": ("COW", "GOOSE"), "skip_care": True, "from_step": 144},
    "fl_cowgoose_feedonly": {"animals": ("COW", "GOOSE"), "skip_care": False, "from_step": 144},
    "fl_cow": {"animals": ("COW",), "skip_care": True, "from_step": 144},
    "fl_all": {"animals": ("COW", "GOOSE", "SHEEP"), "skip_care": True, "from_step": 144},
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="lead5")
    a = ap.parse_args()
    src = (VD / f"{a.base}.py").read_text().rstrip()
    receipt = {}
    for name, cfg in VARIANTS.items():
        out = VD / f"{a.base}_{name}.py"
        out.write_text(src + "\n" + WRAPPER.replace("@@CFG@@", repr(cfg)))
        receipt[out.stem] = {"base": a.base, "cfg": cfg, "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print("built", out.name)
    (ROOT / "experiments" / "v43_feed_less_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
