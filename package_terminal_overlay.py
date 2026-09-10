#!/usr/bin/env python3
"""Promote Terminal D locally and build its deterministic upload archive."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "agents/shop_router_0909_terminal_d_market_smart_2pass"
SELECTED = ROOT / "agents/shop_router_0909_terminal"
SUBMISSION = ROOT / "submission"
FILES = (
    "main.py", "policy.py", "router_parent.py", "terminal_planner.py",
    "unit_model.py", "settings.json", "actions.json", "LICENSE.txt", "NOTICE.md",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bundle_sha(directory):
    material = "".join(f"{name}\0{sha(directory/name)}\n" for name in FILES).encode()
    return hashlib.sha256(material).hexdigest()


def make_archive(path):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name in FILES:
            data = (SUBMISSION / name).read_bytes()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
    with path.open("wb") as stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as zipped:
            zipped.write(buffer.getvalue())


def main():
    SELECTED.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copyfile(SOURCE / name, SELECTED / name)
    notice = (
        "# Attribution and selected terminal-overlay provenance\n\n"
        "This selected candidate preserves ShopRouter0909Hardened exactly through step 711, "
        "including its Plan-10 correction. At steps 712–718 it applies the Apache-2.0 "
        "Market-Smart public physical closure planner, with only its bounded search budget "
        "raised from 256/1/16 to 512 simulations, two passes, and 32 proposals per actor. "
        "The candidate was selected locally on Kaggriculture 1.32.7 and has not been submitted "
        "to Kaggle by this packaging script.\n"
    )
    (SELECTED / "NOTICE.md").write_text(notice)
    for name in FILES:
        shutil.copyfile(SELECTED / name, SUBMISSION / name)
    archive = SUBMISSION / "shop_router_0909_terminal.tar.gz"
    make_archive(archive)
    manifest = {
        "schema_version": 1,
        "selected_path": "agents/shop_router_0909_terminal/main.py",
        "source_candidate": "agents/shop_router_0909_terminal_d_market_smart_2pass/main.py",
        "entrypoint_sha256": sha(SELECTED / "main.py"),
        "policy_sha256": sha(SELECTED / "policy.py"),
        "terminal_planner_sha256": sha(SELECTED / "terminal_planner.py"),
        "bundle_sha256": bundle_sha(SELECTED),
        "files": {name: sha(SELECTED / name) for name in FILES},
        "archive_path": "submission/shop_router_0909_terminal.tar.gz",
        "archive_sha256": sha(archive),
        "archive_members": list(FILES),
        "kaggle_submission_performed": False,
    }
    (EXP := ROOT / "experiments").mkdir(exist_ok=True)
    (EXP / "terminal_overlay_package_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
