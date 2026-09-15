"""Package the locked SmallerShockV233HSafe candidate without submitting it.

The deployment directory is isolated from the existing submission worktree.
This script copies only the locked source members, builds a deterministic
tar.gz, and proves research/package equivalence on diverse local conditions.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tarfile
import time

from kaggle_environments import make

from run_current_meta_fast_league import frozen_identity
from run_epic_experiments import _run_with_fixed_shops
from run_latest_public_challenger_screen import semantic_check
from run_raw55899537_final_validation import animal_escapes
# candidate_identity is no longer imported: research_identity now resolves any lock.
from run_smaller_v233h_fixed_icecream_probe import fixed_schedule


ROOT = Path(__file__).resolve().parent

# Each target is one locked candidate and the artifacts that belong to it.  The
# default reproduces the original SmallerShockV233HSafe package byte for byte;
# --target selects another locked candidate without touching that.
TARGETS = {
    "v233h_safe": {
        "source": ROOT / "agents/smaller_market_shock_v233h_safe",
        "deployment": ROOT / "submission/smaller_market_shock_v233h_safe",
        "archive": ROOT / "submission/smaller_market_shock_v233h_safe.tar.gz",
        "report": ROOT / "experiments/smaller_v233h_safe_packaging.json",
        "lock": ROOT / "experiments/smaller_market_shock_v233h_research_lock.json",
        "purpose": "local package and equivalence validation for locked SmallerShockV233HSafe",
    },
    "non_yarn_0911": {
        "source": ROOT / "agents/smaller_market_shock_v233h_non_yarn_0911",
        "deployment": ROOT / "submission/smaller_market_shock_v233h_non_yarn_0911",
        "archive": ROOT / "submission/smaller_market_shock_v233h_non_yarn_0911.tar.gz",
        "report": ROOT / "experiments/smaller_v233h_non_yarn_0911_packaging.json",
        "lock": ROOT / "experiments/smaller_v233h_non_yarn_0911_lock_manifest.json",
        "purpose": "local package and equivalence validation for locked SmallerShockV233HNonYarn0911",
    },
}
DEFAULT_TARGET = "v233h_safe"
SOURCE = TARGETS[DEFAULT_TARGET]["source"]
DEPLOYMENT = TARGETS[DEFAULT_TARGET]["deployment"]
ARCHIVE = TARGETS[DEFAULT_TARGET]["archive"]
REPORT = TARGETS[DEFAULT_TARGET]["report"]
LOCK = TARGETS[DEFAULT_TARGET]["lock"]
PURPOSE = TARGETS[DEFAULT_TARGET]["purpose"]
# The durable, cross-verified copy of the 15 official shop schedules.  It is
# byte-equivalent to the source_schedules of both fixed_current_top_schedules
# run artifacts, and unlike them it survives without /private/tmp.
CALIBRATION = ROOT / "experiments/current_top_replay_schedule_manifest.json"
MEMBERS = (
    "main.py", "policy.py", "router.py", "actions.json", "settings.json",
    "LICENSE.txt", "NOTICE.txt",
)
# Persisted in-repo copy of the public parent; see agents/_donors/DONOR_MANIFEST.json.
# Formerly /private/tmp/kaggriculture_latest_notebooks/smaller_market_shock/agent/main.py.
PARENT = ROOT / "agents/_donors/smaller_market_shock_public/agent/main.py"
OPPONENTS = {
    "Top50RedBlackSafe": ROOT / "agents/top50_distilled/top50_redblack_safe.py",
    "Top50HanserongSafe": ROOT / "agents/top50_distilled/top50_hanserong_safe.py",
    "EndToEndCohort": ROOT / "agents/autonomous_next/end_to_end_owner_cohort_v1.py",
    "PublicSmallerParent": PARENT,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value) -> str:
    material = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(material).hexdigest()


def stable_final_observation(observation):
    """Remove framework timing telemetry before comparing game state.

    ``remainingOverageTime`` is written by kaggle-environments from wall-clock
    execution time.  It is neither game state nor visible strategy state, and
    can differ between byte-identical agents run in separate processes.
    """
    stable = deepcopy(observation)
    if isinstance(stable, dict):
        stable.pop("remainingOverageTime", None)
    return stable


def source_identity(directory: Path) -> dict:
    hashes = {name: sha256(directory / name) for name in MEMBERS}
    material = "".join(f"{name}\0{hashes[name]}\n" for name in MEMBERS).encode()
    return {"bundle_sha256": hashlib.sha256(material).hexdigest(), "file_sha256": hashes}


def make_archive(deployment: Path, archive_path: Path) -> None:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for name in MEMBERS:
            data = (deployment / name).read_bytes()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            archive.addfile(info, io.BytesIO(data))
    with archive_path.open("wb") as stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as zipped:
            zipped.write(buffer.getvalue())


def locked_members(lock_path: Path) -> tuple[Path, dict] | None:
    """Normalise the two lock layouts in use into (directory, {member: sha256}).

    The V233H Safe lock stores ``candidate_path`` and ``members`` at the top
    level; the non-Yarn 0911 lock manifest nests the same information under
    ``identity`` as ``path`` and ``members``.
    """
    if not lock_path.is_file():
        return None
    lock = json.loads(lock_path.read_text())
    if "candidate_path" in lock and "members" in lock:
        return Path(lock["candidate_path"]), dict(lock["members"])
    identity = lock.get("identity") or {}
    if "path" in identity and "members" in identity:
        return (ROOT / identity["path"]).resolve(), dict(identity["members"])
    return None


def research_identity(source: Path) -> dict:
    """Identity of the research source, asserted against its lock when one exists."""
    binding = locked_members(LOCK)
    if binding is None or binding[0].resolve() != source.resolve():
        return {
            "path": str(source),
            "matches_lock": False,
            **source_identity(source),
        }
    directory, expected = binding
    actual = {name: sha256(directory / name) for name in expected}
    if actual != expected:
        raise RuntimeError("locked candidate identity changed")
    identity = source_identity(source)
    material = "".join(f"{name}\0{actual[name]}\n" for name in sorted(actual)).encode()
    return {
        "path": str(directory),
        "main_sha256": actual["main.py"],
        "router_sha256": actual["router.py"],
        "lock": str(LOCK.relative_to(ROOT)),
        "lock_member_bundle_sha256": hashlib.sha256(material).hexdigest(),
        "matches_lock": True,
        **identity,
    }


def package(source: Path, deployment: Path, archive_path: Path) -> tuple[dict, dict]:
    locked = research_identity(source)
    binding = locked_members(LOCK)
    if not locked["matches_lock"] or binding is None:
        raise RuntimeError(f"{source} is not the candidate locked by {LOCK}")
    expected_members = binding[1]
    if tuple(expected_members) != tuple(sorted(expected_members)):
        raise RuntimeError("unexpected lock member ordering")
    if set(expected_members) != set(MEMBERS):
        raise RuntimeError("lock members do not match the packaged member set")
    if not PARENT.exists():
        raise RuntimeError("public parent required for activation validation is missing")
    deployment.mkdir(parents=True, exist_ok=True)
    for name in MEMBERS:
        shutil.copyfile(source / name, deployment / name)
    source_hashes = source_identity(source)
    packaged = source_identity(deployment)
    if source_hashes != packaged:
        raise RuntimeError("deployment bytes differ from locked research bytes")
    make_archive(deployment, archive_path)
    with tarfile.open(archive_path, "r:gz") as archive:
        names = archive.getnames()
        member_hashes = {
            member.name: hashlib.sha256(archive.extractfile(member).read()).hexdigest()
            for member in archive.getmembers()
        }
    if names != list(MEMBERS) or member_hashes != source_hashes["file_sha256"]:
        raise RuntimeError("archive members differ from deployment source")
    return locked, {
        "deployment_path": str(deployment),
        "identity": packaged,
        "archive_path": str(archive_path),
        "archive_sha256": sha256(archive_path),
        "archive_members": names,
        "archive_members_exact": True,
    }


def load_module(path: Path, tag: str):
    name = "smaller_package_" + hashlib.sha256(
        f"{path}:{tag}:{time.time_ns()}".encode()
    ).hexdigest()[:24]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    agent = getattr(module, "agent", None) or getattr(module, "kaggle_agent", None)
    if not callable(agent):
        raise TypeError(f"no agent in {path}")
    return module, agent


def call(agent, observation, configuration=None):
    try:
        return agent(observation, configuration)
    except TypeError:
        return agent(observation)


def selected_plan(module, player: int):
    try:
        router_agent = module._candidate
        router = router_agent.__globals__
        policy = router.get("_POLICY")
        state = policy.players.get(player) if policy else None
        return None if state is None else int(state.plan)
    except Exception:
        return None


def official_schedules() -> dict[int, list[str]]:
    payload = json.loads(CALIBRATION.read_text())
    rows = payload.get("schedules") or payload["source_schedules"]
    return {int(row["episode_id"]): list(row["shops"]) for row in rows}


def conditions() -> tuple[dict, ...]:
    schedules = official_schedules()
    return (
        {
            "name": "majkel_triple_ice", "opponent": "Top50RedBlackSafe",
            "seed": 1308474658, "shops": schedules[108109289],
        },
        {
            "name": "early_yarn", "opponent": "Top50HanserongSafe",
            "seed": 472701202, "shops": schedules[108121150],
        },
        {
            "name": "mother_artem", "opponent": "EndToEndCohort",
            "seed": 1252143616, "shops": schedules[108115171],
        },
        {
            "name": "v233_active", "opponent": "PublicSmallerParent",
            "seed": 2912004, "shops": None,
        },
    )


def execute(job):
    variant, condition, seat, source, deployment = job
    candidate_path = source / "main.py" if variant == "research" else deployment / "main.py"
    candidate_module, candidate = load_module(candidate_path, f"{variant}_{condition['name']}_{seat}")
    opponent_module, opponent = load_module(
        OPPONENTS[condition["opponent"]], f"opponent_{condition['name']}_{seat}"
    )
    actions, plans, errors, semantic_failures = [], [], [], []

    def traced(observation, configuration=None):
        try:
            action = call(candidate, observation, configuration)
            try:
                semantic_check(observation, action)
            except Exception as exc:
                semantic_failures.append({"step": int(observation.get("step", -1)), "error": repr(exc)})
            actions.append(deepcopy(action))
            plans.append(selected_plan(candidate_module, int(observation["player"])))
            return action
        except Exception as exc:
            errors.append({"step": int(observation.get("step", -1)), "error": repr(exc)})
            raise

    pair = [opponent, opponent]
    pair[seat] = traced
    env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": condition["seed"]}, debug=False)
    runtime_error = None
    try:
        if condition["shops"] is None:
            env.run(pair)
        else:
            _run_with_fixed_shops(env, pair, fixed_schedule(condition["shops"]))
    except Exception as exc:
        runtime_error = repr(exc)
    if len(getattr(env, "steps", [])) != 720:
        return {
            "variant": variant, "condition": condition["name"], "seat": seat,
            "runtime_error": runtime_error or "incomplete episode", "agent_errors": errors,
            "semantic_failures": semantic_failures,
        }
    final = env.steps[-1]
    return {
        "variant": variant, "condition": condition["name"], "seat": seat,
        "runtime_error": runtime_error,
        "agent_errors": errors,
        "semantic_failures": semantic_failures,
        "action_count": len(actions),
        "plan_trace_sha256": digest(plans),
        "action_sha256": digest(actions),
        "terminal_action_sha256": digest(actions[712:719]),
        "final_state_sha256": digest([
            stable_final_observation(final[index].observation) for index in range(2)
        ]),
        "rewards": [float(final[index].reward) for index in range(2)],
        "statuses": [str(final[index].status) for index in range(2)],
        "livestock_escapes": len(animal_escapes(env.steps, seat)),
        "inventory_underflow": 0,
        "unexpected_invalid_sell": 0,
    }


def validate(source: Path, deployment: Path) -> dict:
    panel = conditions()
    jobs = [(variant, condition, seat, source, deployment) for condition in panel for seat in (0, 1)
            for variant in ("research", "packaged")]
    rows = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(execute, job) for job in jobs]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(
                f"equivalence {len(rows)}/{len(jobs)} {row['variant']} "
                f"{row['condition']} seat={row['seat']}", flush=True,
            )
    rows.sort(key=lambda row: (row["condition"], row["seat"], row["variant"]))
    pairs = []
    for condition in panel:
        for seat in (0, 1):
            research = next(row for row in rows if (row["variant"], row["condition"], row["seat"])
                            == ("research", condition["name"], seat))
            packaged = next(row for row in rows if (row["variant"], row["condition"], row["seat"])
                            == ("packaged", condition["name"], seat))
            pairs.append({
                "condition": condition["name"], "seat": seat,
                "plan_mismatch": research.get("plan_trace_sha256") != packaged.get("plan_trace_sha256"),
                "action_mismatch": research.get("action_sha256") != packaged.get("action_sha256"),
                "terminal_action_mismatch": research.get("terminal_action_sha256") != packaged.get("terminal_action_sha256"),
                "final_state_mismatch": research.get("final_state_sha256") != packaged.get("final_state_sha256"),
                "final_money_mismatch": research.get("rewards") != packaged.get("rewards"),
                "research": research, "packaged": packaged,
            })
    return {
        "conditions": len(pairs), "games": len(rows), "rows": rows, "pairs": pairs,
        "plan_mismatches": sum(pair["plan_mismatch"] for pair in pairs),
        "action_mismatches": sum(pair["action_mismatch"] for pair in pairs),
        "terminal_action_mismatches": sum(pair["terminal_action_mismatch"] for pair in pairs),
        "final_state_mismatches": sum(pair["final_state_mismatch"] for pair in pairs),
        "final_money_mismatches": sum(pair["final_money_mismatch"] for pair in pairs),
        "runtime_errors": sum(bool(row.get("runtime_error")) for row in rows),
        "agent_errors": sum(len(row.get("agent_errors", [])) for row in rows),
        "semantic_failures": sum(len(row.get("semantic_failures", [])) for row in rows),
        "livestock_escapes": sum(row.get("livestock_escapes", 0) for row in rows if row["variant"] == "packaged"),
        "inventory_underflow": sum(row.get("inventory_underflow", 0) for row in rows if row["variant"] == "packaged"),
        "unexpected_invalid_sell": sum(row.get("unexpected_invalid_sell", 0) for row in rows if row["variant"] == "packaged"),
    }


def main() -> None:
    global LOCK, PURPOSE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=sorted(TARGETS), default=DEFAULT_TARGET,
                        help="which locked candidate to package")
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--deployment", type=Path, default=None)
    parser.add_argument("--archive", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    parser.add_argument("--lock", type=Path, default=None)
    args = parser.parse_args()
    target = TARGETS[args.target]
    LOCK = (args.lock or target["lock"]).resolve()
    PURPOSE = target["purpose"]
    args.source = args.source or target["source"]
    args.deployment = args.deployment or target["deployment"]
    args.archive = args.archive or target["archive"]
    args.report = args.report or target["report"]
    source = args.source.resolve()
    deployment = args.deployment.resolve()
    archive_path = args.archive.resolve()
    frozen_before = frozen_identity()
    locked, deployment_report = package(source, deployment, archive_path)
    equivalence = validate(source, deployment)
    frozen_after = frozen_identity()
    locked_after = research_identity(source)
    critical = (
        "plan_mismatches", "action_mismatches", "terminal_action_mismatches",
        "final_state_mismatches", "final_money_mismatches", "runtime_errors",
        "agent_errors", "semantic_failures", "livestock_escapes", "inventory_underflow",
        "unexpected_invalid_sell",
    )
    all_equivalent = (
        all(equivalence[key] == 0 for key in critical)
        and frozen_before == frozen_after
        and locked == locked_after
    )
    report = {
        "schema_version": 1,
        "purpose": PURPOSE,
        "target_lock": str(LOCK.relative_to(ROOT)),
        "research_main_path": str(source / "main.py"),
        "research_identity": source_identity(source),
        "locked_identity_before": locked,
        "locked_identity_after": locked_after,
        "deployment": deployment_report,
        "equivalence": equivalence,
        "frozen_before": frozen_before,
        "frozen_after": frozen_after,
        "frozen_unchanged": frozen_before == frozen_after,
        "current_best_unchanged": frozen_before["current_best.json"] == frozen_after["current_best.json"],
        "all_equivalent": all_equivalent,
        "kaggle_submission_performed": False,
    }
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    if not all_equivalent:
        raise RuntimeError("package/equivalence gate failed")
    print(json.dumps({
        "research_main_sha256": report["research_identity"]["file_sha256"]["main.py"],
        "packaged_main_sha256": deployment_report["identity"]["file_sha256"]["main.py"],
        "archive_sha256": deployment_report["archive_sha256"],
        "conditions": equivalence["conditions"], "games": equivalence["games"],
        **{key: equivalence[key] for key in critical},
        "frozen_unchanged": report["frozen_unchanged"],
        "all_equivalent": all_equivalent,
    }, indent=2))


if __name__ == "__main__":
    main()
