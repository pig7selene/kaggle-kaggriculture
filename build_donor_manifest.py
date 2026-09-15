"""Regenerate agents/_donors/DONOR_MANIFEST.json from the copied donor bytes."""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DONORS = ROOT / "agents/_donors"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(directory):
    return {
        str(p.relative_to(directory)): {"sha256": sha(p), "bytes": p.stat().st_size}
        for p in sorted(directory.rglob("*")) if p.is_file()
    }


def kernel_ref(directory):
    meta = directory / "kernel-metadata.json"
    if not meta.is_file():
        return None
    payload = json.loads(meta.read_text())
    ref = payload.get("id")
    return f"https://www.kaggle.com/code/{ref}" if ref else None


salvaged = json.loads((DONORS / "current_meta_agents/manifest.json").read_text())
recorded = {row["candidate"]: row for row in salvaged["candidates"]}
present = {p.name for p in (DONORS / "current_meta_agents").iterdir() if p.is_dir()}

manifest = {
    "schema_version": 1,
    "purpose": (
        "Persistent copies of the external donor assets that the in-repo research "
        "candidates were built and validated against. Copied out of /private/tmp, "
        "which macOS reaps. Every entry is byte-identical to the /private/tmp source "
        "at copy time and to the SHA-256 recorded in the corresponding build receipt "
        "or research lock."
    ),
    "copied_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "license_note": (
        "All donor sources are public Apache-2.0 Kaggle notebooks. Their own LICENSE "
        "and NOTICE files are preserved verbatim. No donor source is redistributed as "
        "our own work; see each agent's NOTICE for the attribution chain."
    ),
    "kaggle_submission_made": False,
    "donors": {
        "shop_router_0911_simple": {
            "role": "route donor for smaller_market_shock_v233h_non_yarn_0911",
            "origin_tmp_path": "/private/tmp/kaggriculture_shop_router_0911_simple",
            "kaggle_url": kernel_ref(DONORS / "shop_router_0911_simple"),
            "consumed_by": ["build_smaller_v233h_non_yarn_0911.py"],
            "supplies": "14 fixed tapes and 64 ordered shop-pair mappings; 42 non-Yarn continuations were transplanted",
            "files": files(DONORS / "shop_router_0911_simple"),
        },
        "smaller_market_shock_public": {
            "role": "public parent of the whole V233H lineage",
            "origin_tmp_path": "/private/tmp/kaggriculture_latest_notebooks/smaller_market_shock",
            "kaggle_url": kernel_ref(DONORS / "smaller_market_shock_public"),
            "consumed_by": [
                "package_smaller_v233h_safe.py (PublicSmallerParent equivalence opponent)",
                "run_latest_public_challenger_screen.py (SmallerMarketShock)",
                "build_smaller_market_shock_v233_hybrid.py (SOURCE)",
            ],
            "files": files(DONORS / "smaller_market_shock_public"),
        },
        "soil_remembers_rain_public": {
            "role": "source notebook of the exact V233/V234 six-sheep module embedded in the candidate",
            "origin_tmp_path": "/private/tmp/kaggriculture_latest_notebooks/soil_remembers_rain",
            "kaggle_url": kernel_ref(DONORS / "soil_remembers_rain_public"),
            "note": (
                "The extracted executable form (current_meta_agents/soil_v235_combined/main.py, "
                "sha256 6c1f6dfa29f1064608f7760e827897aa6c590f9ba7550ecff23610c5ecabac2d) was "
                "already lost to the /private/tmp reaper before this copy. This notebook is the "
                "remaining recovery path for that module's provenance."
            ),
            "files": files(DONORS / "soil_remembers_rain_public"),
        },
        "current_meta_agents": {
            "role": "intermediate build chain for smaller_market_shock_v233h_safe, plus the salvaged origin record of the lost public opponents",
            "origin_tmp_path": "/private/tmp/current_meta_agents",
            "consumed_by": [
                "build_smaller_v233h_safe.py (SOURCE = smaller_market_shock_v233_hybrid)",
                "run_current_meta_fast_league.py / run_current_meta_deep_validation.py / run_latest_public_challenger_screen.py (opponent table)",
            ],
            "files": files(DONORS / "current_meta_agents"),
        },
    },
    "lost_before_copy": {
        "note": (
            "These assets were already emptied by the macOS /private/tmp reaper (observed "
            "2026-09-15) before this migration ran. They are NOT recovered here. Their origin "
            "and SHA-256 survive in agents/_donors/current_meta_agents/manifest.json, so each "
            "is re-downloadable from Kaggle with a verifiable identity check."
        ),
        "current_meta_agents": sorted(
            {name: row for name, row in recorded.items() if name not in present}
        ),
        "current_meta_agents_detail": [
            {k: row[k] for k in ("candidate", "origin", "bytes", "main_sha256") if k in row}
            for name, row in sorted(recorded.items()) if name not in present
        ],
        "other_directories": [
            {"path": "/private/tmp/lb_gap_opponents", "contained": "market_smart, most_powerfull, farming_v3_current, shape_shop_current, seven_rescue",
             "breaks": ["run_wlt_benchmark_v1.py", "run_front_run_candidates.py", "package_front_run_candidate.py",
                        "run_terminal_overlay_sprint.py", "validate_terminal_overlay_packaging.py", "run_terminal_d_tie_diagnostics.py"]},
            {"path": "/private/tmp/v27_exact", "contained": "exact public V27 front-running agent and archive",
             "breaks": ["run_v27_front_running.py", "build_v27_front_running_artifacts.py"]},
        ],
    },
}

path = DONORS / "DONOR_MANIFEST.json"
path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
print(path)
print(json.dumps({
    "donors": {k: len(v["files"]) for k, v in manifest["donors"].items()},
    "lost_current_meta_agents": manifest["lost_before_copy"]["current_meta_agents"],
}, indent=2))
