"""Remap the 21 route-105 pairs to route 124 on the room_plus_clamp base.

This is the remap tier's one survivor. In the pilot route 124 was the best of
27 routes on 11 of the 21 pairs and the best on average (+398 over 105); on the
four pairs re-tested on unseen seeds it was positive on all four (+296 to
+622). It is not worth a submission by itself -- a few points blended -- but it
is a one-line change that costs nothing to carry.

The remap is injected before V43's base agent is constructed, the lesson of the
hybrid: V43's main.py is a 3,366-line overlay stack and anything appended at
the end binds to nothing. Route 124 already exists in the bank, so the route
count and therefore memory are unchanged.

``--check`` plays a few seeds against the unmodified room_plus_clamp baseline:
on pairs outside the 21 the two must be behaviourally identical (margin exactly
zero), which is the wiring test that caught the hybrid's first bug.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import time


ROOT = Path(__file__).resolve().parent
BASE = Path("/private/tmp/kaggriculture_v43_variants/room_plus_clamp.py")
ROUTEMAP = Path("/tmp/v43_routemap.json")
SEEDS = ROOT / "experiments" / "seed_first_shops_manifest.json"
OUT_PY = Path("/private/tmp/kaggriculture_v43_variants/room_clamp_r124.py")
ARCHIVE = ROOT / "submission" / "v43_room_clamp_r124.tar.gz"
RECEIPT = ROOT / "experiments" / "v43_room_clamp_r124_build.json"
ANCHOR = "_IMPL=make_agent(_ROUTES,router=_router,**_SETTINGS)"
TARGET_ROUTE = 124


def build() -> tuple[bytes, list[list[str]]]:
    source = BASE.read_text()
    if source.count(ANCHOR) != 1:
        raise RuntimeError(f"expected one anchor, found {source.count(ANCHOR)}")
    pairs = json.loads(ROUTEMAP.read_text())["pairs_105"]
    block = (
        "\n# Remap: the 21 pairs V43 sends to route 105 go to route 124 instead, which\n"
        "# ranked best on average across them in experiments/route_remap_pilot.md and\n"
        "# stayed positive on every pair re-tested on unseen seeds.\n"
        "_R108_SHOP_ROUTES.update({\n"
        + "".join(f"    {tuple(p)!r}: {TARGET_ROUTE},\n" for p in pairs)
        + "})\n\n"
    )
    text = source.replace(ANCHOR, block + ANCHOR, 1)
    OUT_PY.write_text(text)
    return text.encode(), pairs


def package(data: bytes) -> str:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tf:
            info = tarfile.TarInfo("main.py")
            info.size, info.mtime, info.uid, info.gid, info.mode = len(data), 0, 0, 0, 0o644
            info.uname = info.gname = ""
            tf.addfile(info, io.BytesIO(data))
    ARCHIVE.write_bytes(buf.getvalue())
    return hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()


def load(path: Path, tag: str):
    import importlib.util
    name = "r124_" + hashlib.sha256(f"{path}:{tag}:{time.time_ns()}".encode()).hexdigest()[:20]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return name, (getattr(module, "agent", None) or getattr(module, "kaggle_agent"))


def check(pairs: list[list[str]]) -> dict:
    """Two covered and two uncovered pairs, both seats: uncovered must be margin 0."""
    import gc
    from kaggle_environments import make
    by_pair = json.loads(SEEDS.read_text())["by_pair"]
    covered = {" + ".join(p) for p in pairs}
    picks = [(pair, seeds[0], True) for pair, seeds in by_pair.items() if pair in covered][:2]
    picks += [(pair, seeds[0], False) for pair, seeds in by_pair.items()
              if pair not in covered and "YARN_STORE" not in pair][:2]
    rows = []
    for pair, seed, is_covered in picks:
        for seat in (0, 1):
            n1, new = load(OUT_PY, f"n{seed}{seat}")
            n2, base = load(BASE, f"b{seed}{seat}")
            players = [None, None]
            players[seat], players[1 - seat] = new, base
            env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False)
            env.run(players)
            final = env.steps[-1]
            margin = float(final[seat].reward) - float(final[1 - seat].reward)
            rows.append({"pair": pair, "seed": seed, "seat": seat, "covered": is_covered,
                         "margin": margin, "complete": len(env.steps) == 720})
            for n in (n1, n2):
                sys.modules.pop(n, None)
            del env
            gc.collect()
    uncovered_ok = all(r["margin"] == 0 and r["complete"] for r in rows if not r["covered"])
    return {"rows": rows, "uncovered_identical": uncovered_ok,
            "covered_margins": [r["margin"] for r in rows if r["covered"]]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    data, pairs = build()
    main_sha = hashlib.sha256(data).hexdigest()
    archive_sha = package(data)
    receipt = {
        "purpose": "room_plus_clamp with the 21 route-105 pairs remapped to route 124",
        "base": str(BASE), "target_route": TARGET_ROUTE, "pairs_remapped": pairs,
        "evidence": ["experiments/route_remap_pilot.md", "experiments/route_remap_holdout.md"],
        "main_sha256": main_sha, "archive": str(ARCHIVE.relative_to(ROOT)),
        "archive_sha256": archive_sha, "archive_bytes": ARCHIVE.stat().st_size,
        "kaggle_submission_made": False,
    }
    if args.check:
        receipt["wiring_check"] = check(pairs)
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "pairs_remapped"}, indent=2))


if __name__ == "__main__":
    main()
