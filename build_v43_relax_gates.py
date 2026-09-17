"""Let V43's own fourth-quadrant investments fire more often.

The shipped notebook already carries two conditional expansions into the
south-east quadrant: `_v233` buys the land, six sheep and two hands when the
town has at least two YARN_STOREs and wool is at 220 or more on day 12, and
`_v219` plants tomatoes there from day 18 when three PIZZA_SHOP or
FARMERS_MARKET shops are open. In a typical V43 game wool ends the season
112 units short of what the town wanted, pinned at its ceiling price of 241,
and tomatoes 228 short at 87 -- with a single yarn store the sheep gate misses
by a few dollars and the demand goes unserved. Each gate is a comparison in
one line; these variants loosen them and let the author's machinery decide.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")

EDITS = {
    "yarn1": ("obs['town']['unlocked_shops'].count('YARN_STORE')<2", "obs['town']['unlocked_shops'].count('YARN_STORE')<1"),
    "wool200": ("prices['WOOL']<220", "prices['WOOL']<200"),
    "wool180": ("prices['WOOL']<220", "prices['WOOL']<180"),
    "pizza2": ("sum(s in ('PIZZA_SHOP','FARMERS_MARKET') for s in obs['town']['unlocked_shops']) < 3",
               "sum(s in ('PIZZA_SHOP','FARMERS_MARKET') for s in obs['town']['unlocked_shops']) < 2"),
    "money8k": ("farm['money'] < 12000", "farm['money'] < 8000"),
}
VARIANTS = {
    "rg_y1": ["yarn1"],
    "rg_y1_w200": ["yarn1", "wool200"],
    "rg_y1_w180": ["yarn1", "wool180"],
    "rg_p2": ["pizza2"],
    "rg_p2_m8": ["pizza2", "money8k"],
    "rg_all": ["yarn1", "wool200", "pizza2", "money8k"],
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="lead5")
    a = ap.parse_args()
    src = (VD / f"{a.base}.py").read_text()
    for k, (old, _) in EDITS.items():
        assert src.count(old) == 1, (k, src.count(old))
    receipt = {}
    for name, edits in VARIANTS.items():
        s = src
        for e in edits:
            old, new = EDITS[e]
            s = s.replace(old, new)
        out = VD / f"{a.base}_{name}.py"
        out.write_text(s)
        receipt[out.stem] = {"base": a.base, "edits": edits, "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}
        print("built", out.name)
    (ROOT / "experiments" / "v43_relax_gates_build.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
