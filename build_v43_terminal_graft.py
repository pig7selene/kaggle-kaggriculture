"""Graft Terminal D's searched endgame onto the V43 room_plus_clamp base.

Terminal D is the only artefact in this repository with an online gain of the
size we need and a clean attribution: it kept Shop Router 0909 Hardened
byte-identical through step 711 and replaced only steps 712-718 with a bounded
physical search over the hands' final actions plus a liquidation, and went from
2377.9 to 2496.8. Its planner is state-driven -- it takes the live observation
and simulates -- so this is not a tape transplant.

Two facts make V43 the right host. V43's farm plan is the same plan Terminal D's
planner was built for (150/265 land, 75 tiles, 11 hands, 8/6/3 animals, same
seed purchases to the unit), so the physical model already fits the layout. And
V43's own endgame is the naive one the planner improved on: from step 712 its
route 2 posts SELL x 1000 on every product and leaves most hands on PASS -- 8
of 9 hands idle at 717, all 9 at 718.

Wiring differs from Terminal D's own in one respect. Terminal D shadow-runs its
parent for 712-718 to obtain the exact baseline schedule; V43's state lives in
closures a wrapper cannot clone. The baseline here is the parent's real step-712
action followed by V43 route 2's raw tape for 713-718. terminal_action() checks
at every step that the physical state and the parent's effective action still
match the plan, and abandons to the parent action if not, so a baseline that
drifts costs a missed gain, never a broken game. Acceptance and abandonment are
counted in telemetry so the A/B can see how often the plan actually ran.

Output is a multi-file agent directory (main.py plus the three planner modules,
copied byte-for-byte from agents/shop_router_0909_terminal) and a deterministic
tar.gz, the same shape Terminal D itself was submitted in.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile


ROOT = Path(__file__).resolve().parent
BASE = Path("/private/tmp/kaggriculture_v43_variants/room_plus_clamp.py")
PLANNER_SRC = ROOT / "agents" / "shop_router_0909_terminal"
PLANNER_FILES = ("terminal_planner.py", "unit_model.py", "router_parent.py")
OUT_DIR = ROOT / "agents" / "v43_terminal_graft"
ARCHIVE = ROOT / "submission" / "v43_terminal_graft.tar.gz"
RECEIPT = ROOT / "experiments" / "v43_terminal_graft_build.json"

WRAPPER = '''

# ---------------------------------------------------------------- terminal graft
# Terminal D's bounded physical endgame planner (agents/shop_router_0909_terminal,
# steps 712-718) on top of the V43 chassis. Never raises: any failure returns
# the parent's action unchanged.
import os as _tg_os
import sys as _tg_sys
import importlib.util as _tg_ilu

_TG_DIR = _tg_os.path.dirname(_tg_os.path.abspath(__file__))
if _TG_DIR not in _tg_sys.path:
    _tg_sys.path.insert(0, _TG_DIR)


def _tg_sibling(name):
    spec = _tg_ilu.spec_from_file_location(name, _tg_os.path.join(_TG_DIR, name + ".py"))
    module = _tg_ilu.module_from_spec(spec)
    _tg_sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


for _tg_name in ("unit_model", "router_parent"):
    if _tg_name not in _tg_sys.modules:
        _tg_sibling(_tg_name)
_TG_PLANNER = _tg_sibling("terminal_planner")
_TG_START, _TG_FINAL = _TG_PLANNER.START, _TG_PLANNER.FINAL
# The planner's mismatch test compares field commands AND the full market list.
# Our baseline for 713-718 is route 2's raw tape, whose SELL x 1000 orders V43's
# clamp_sells has already trimmed in the parent's real action, so the market
# side never matches and every plan was abandoned at 713 (20 of 20 in the
# first A/B). The planner certifies it changes no market before the final step,
# so compare commands only; the market is taken from the parent below.
_TG_PLANNER._effective_action = lambda action, n: _TG_PLANNER._commands(action, n)
_TG_SETTINGS = {"max_simulations": @@SIMS@@, "passes": @@PASSES@@, "proposals_per_actor": @@PROPS@@}
_TG_PARENT = agent
_TG_STATE = {}
_TG_TELEMETRY = {"invocations": 0, "accepted": 0, "abandoned": 0, "activated_steps": 0,
                 "errors": 0, "reasons": []}


def _tg_int(value, default=-1):
    try:
        return int(value)
    except Exception:
        return default


def agent(observation, configuration=None):
    action = _TG_PARENT(observation, configuration)
    try:
        step = _tg_int(observation.get("step") if isinstance(observation, dict)
                       else getattr(observation, "step", -1))
        seat = _tg_int(observation.get("player") if isinstance(observation, dict)
                       else getattr(observation, "player", 0), 0)
        if step < _TG_START or step > _TG_FINAL:
            if step == 0:
                _TG_STATE.pop(seat, None)
            return action
        state = _TG_STATE.setdefault(seat, {"plan": None, "last_step": None})
        if step == _TG_START and state["plan"] is None:
            baseline = [action] + [_ROUTES[2][s] for s in range(_TG_START + 1, _TG_FINAL + 1)]
            _TG_TELEMETRY["invocations"] += 1
            plan = _TG_PLANNER.plan_terminal(observation, configuration, baseline, **_TG_SETTINGS)
            state["plan"] = plan
            _TG_TELEMETRY["reasons"].append(str(plan.get("reason"))[:80])
            if plan.get("accepted"):
                _TG_TELEMETRY["accepted"] += 1
        plan = state["plan"]
        if not plan or not plan.get("accepted"):
            return action
        if state["last_step"] is not None and step != state["last_step"] + 1:
            plan["abandoned"] = True
            plan["reason"] = "nonconsecutive callback"
        state["last_step"] = step
        result = _TG_PLANNER.terminal_action(observation, configuration, action, plan)
        if step < _TG_FINAL and isinstance(result, dict) and result is not action:
            # Keep V43's own (clamped, lead-adjusted) market orders; take only the
            # planner's physical commands. The final step's liquidation is the
            # planner's, computed from the real shed.
            result = dict(result, market=[list(o) for o in (action.get("market") or [])])
        if plan.get("abandoned") and not plan.get("_tg_abandon_counted"):
            _TG_TELEMETRY["abandoned"] += 1
            plan["_tg_abandon_counted"] = True
        if result != action:
            _TG_TELEMETRY["activated_steps"] += 1
        return result
    except Exception as exc:
        _TG_TELEMETRY["errors"] += 1
        if len(_TG_TELEMETRY["reasons"]) < 50:
            _TG_TELEMETRY["reasons"].append("error: " + repr(exc)[:80])
        return action


agent.telemetry = {**(getattr(_TG_PARENT, "telemetry", {}) or {}), "terminal_graft": _TG_TELEMETRY}
kaggle_agent = agent
'''


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-simulations", type=int, default=512)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--proposals-per-actor", type=int, default=32)
    args = parser.parse_args()

    source = BASE.read_text()
    if "_TG_PARENT" in source:
        raise RuntimeError("base already carries the terminal graft")
    if "_ROUTES=" not in source:
        raise RuntimeError("base does not define _ROUTES; wrapper needs route 2's tape")
    wrapper = (WRAPPER.replace("@@SIMS@@", str(args.max_simulations))
                      .replace("@@PASSES@@", str(args.passes))
                      .replace("@@PROPS@@", str(args.proposals_per_actor)))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "main.py").write_text(source.rstrip() + "\n" + wrapper)
    for name in PLANNER_FILES:
        shutil.copyfile(PLANNER_SRC / name, OUT_DIR / name)

    members = ["main.py", *PLANNER_FILES]
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tf:
            for name in members:
                data = (OUT_DIR / name).read_bytes()
                info = tarfile.TarInfo(name)
                info.size, info.mtime, info.uid, info.gid, info.mode = len(data), 0, 0, 0, 0o644
                info.uname = info.gname = ""
                tf.addfile(info, io.BytesIO(data))
    ARCHIVE.write_bytes(buf.getvalue())

    receipt = {
        "purpose": "V43 room_plus_clamp with Terminal D's steps-712-718 physical planner",
        "base": str(BASE), "base_sha256": sha256(BASE),
        "planner_source": str(PLANNER_SRC.relative_to(ROOT)),
        "planner_settings": {"max_simulations": args.max_simulations, "passes": args.passes,
                             "proposals_per_actor": args.proposals_per_actor},
        "members": {name: sha256(OUT_DIR / name) for name in members},
        "planner_files_identical_to_terminal_d": all(
            sha256(OUT_DIR / n) == sha256(PLANNER_SRC / n) for n in PLANNER_FILES),
        "archive": str(ARCHIVE.relative_to(ROOT)), "archive_sha256": sha256(ARCHIVE),
        "archive_bytes": ARCHIVE.stat().st_size,
        "kaggle_submission_made": False,
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
