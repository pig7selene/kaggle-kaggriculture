"""Mechanically package the frozen Shop Router 0909 hardened research agent."""

from __future__ import annotations

import gzip
import hashlib
from pathlib import Path
import shutil
import tarfile


ROOT = Path(__file__).resolve().parent
SUBMISSION = ROOT / "submission"
EXACT_MAIN = ROOT / "agents/shop_router_0909/main.py"
EXACT_ACTIONS = ROOT / "agents/shop_router_0909/actions.json"
HARDENED_MAIN = ROOT / "agents/shop_router_0909_hardened/main.py"
HARDENED_COMMON = ROOT / "agents/shop_router_0909_hardened/common.py"
LICENSE = ROOT / "agents/shop_router_0909_hardened/LICENSE.txt"
NOTICE = ROOT / "agents/shop_router_0909_hardened/NOTICE.md"
ARCHIVE = SUBMISSION / "shop_router_0909_hardened.tar.gz"


EXPECTED = {
    EXACT_MAIN: "d6d74997dc5b483db63d8e39cafa1afeec0f366824e75107e109123f111e866b",
    EXACT_ACTIONS: "17d503f2fd20d59f9c0f14024d1e74a8add8bb9b5561d4d908b45deecb5495ef",
    HARDENED_MAIN: "da5c6df2c71128ce1372a5adaf6d4859f5758e7854b399d6ff634fbca666d8a2",
    HARDENED_COMMON: "a882ec25f64fea67e08f11cd4fe6940eb6509e778f469d9ae39679143e7dcc49",
    LICENSE: "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
    NOTICE: "51ef4107c99caae6b11f199a5d79015ada7fd9e1eb51201aa72bb3e4d5aea17c",
}


OLD_AGENT_BLOCK = '''_POLICY = None


def agent(observation, configuration=None):
    global _POLICY
    if _POLICY is None:
        # Kaggle's source loader omits __file__, but retains the code filename.
        folder = Path(agent.__code__.co_filename).resolve().parent
        _POLICY = Policy(folder)
    return _POLICY.act(observation)
'''


PACKAGED_AGENT_BLOCK = '''_POLICY = None


def agent(observation, configuration=None):
    """Exact public policy plus the locked one-primitive Plan-10 hardening."""
    global _POLICY
    if _POLICY is None:
        # Kaggle's source loader omits __file__, but retains the code filename.
        folder = Path(agent.__code__.co_filename).resolve().parent
        _POLICY = Policy(folder)
    action = _POLICY.act(observation)

    # Local hardening: only Plan 10, only step 360, no action insertion/shift.
    step = int(observation["step"])
    player = int(observation["player"])
    plan = _POLICY.players[player].plan
    if plan == 10 and step == 360:
        if action["farmer"] == ["PICKUP", "WHEAT", 5]:
            action["farmer"][2] = 4
    return action
'''


DEPLOYMENT_NOTICE = '''# SPDX-License-Identifier: Apache-2.0
#
# Deployment packaging of Yusuke Hayashi's public Shop Router 0909 agent,
# public notebook version 1 / run 348430185, with the locally validated
# one-parameter Plan-10 hardening documented in NOTICE.md. The public strategy
# and actions.json remain under Apache License 2.0. See LICENSE.txt.

'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_frozen_inputs():
    for path, expected in EXPECTED.items():
        actual = sha(path)
        if actual != expected:
            raise RuntimeError(f"frozen input mismatch: {path}: {actual} != {expected}")


def build_main():
    exact = EXACT_MAIN.read_text()
    if exact.count(OLD_AGENT_BLOCK) != 1:
        raise RuntimeError("exact agent block did not match exactly once")
    packaged = DEPLOYMENT_NOTICE + exact.replace(OLD_AGENT_BLOCK, PACKAGED_AGENT_BLOCK)
    (SUBMISSION / "main.py").write_text(packaged)


def copy_assets():
    shutil.copyfile(EXACT_ACTIONS, SUBMISSION / "actions.json")
    shutil.copyfile(LICENSE, SUBMISSION / "LICENSE.txt")
    shutil.copyfile(NOTICE, SUBMISSION / "NOTICE.md")


def build_reproducible_archive():
    members = ("main.py", "actions.json", "LICENSE.txt", "NOTICE.md")
    with ARCHIVE.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for name in members:
                    path = SUBMISSION / name
                    info = archive.gettarinfo(str(path), arcname=name)
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    info.mode = 0o644
                    with path.open("rb") as source:
                        archive.addfile(info, source)


def main():
    assert_frozen_inputs()
    build_main()
    copy_assets()
    build_reproducible_archive()
    print("submission/main.py", sha(SUBMISSION / "main.py"))
    print("submission/actions.json", sha(SUBMISSION / "actions.json"))
    print("submission/LICENSE.txt", sha(SUBMISSION / "LICENSE.txt"))
    print("submission/NOTICE.md", sha(SUBMISSION / "NOTICE.md"))
    print("submission/shop_router_0909_hardened.tar.gz", sha(ARCHIVE))


if __name__ == "__main__":
    main()
