"""Append a timestamped reading of every submission's public score.

Every decision in this repository so far has rested on a single-point reading of
a score that turns out to move. The only multi-point history we have is V233H
Safe, which fell 2249.4 to 1983.5 to 1976.5, and the registry's drift table
shows dormant submissions frozen while active ones slide. What we do not know is
the *shape*: whether a fresh submission climbs to its level, overshoots and
settles back, or decays from the start. Without that, there is no principled
answer to how long to wait before a reading means anything.

So this records the curve rather than arguing about it. Run it repeatedly; each
call appends one observation per submission. Named with 'manifest' so the
existing !experiments/*manifest*.json rule keeps it tracked.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parent
KAGGLE = ROOT / ".venv/bin/kaggle"
OUTPUT = ROOT / "experiments" / "submission_score_trajectory_manifest.json"


def read_submissions() -> list[dict]:
    result = subprocess.run(
        [str(KAGGLE), "competitions", "submissions", "kaggriculture"],
        capture_output=True, text=True, timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(f"kaggle CLI failed: {result.stderr.strip()[:300]}")
    rows = []
    for line in result.stdout.splitlines():
        match = re.match(
            r"^\s*(\d{6,})\s+(\S+)\s+(\d{4}-\d{2}-\d{2} \S+)\s+(.*?)\s{2,}"
            r"(SubmissionStatus\.\w+)\s*([\d.]*)\s*([\d.]*)\s*$",
            line,
        )
        if not match:
            continue
        sid, filename, date, description, status, public, _private = match.groups()
        rows.append({
            "submission_id": int(sid),
            "file": filename,
            "submitted_at": date,
            "description": description.strip(),
            "status": status.split(".")[-1],
            "public_score": float(public) if public else None,
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = read_submissions()

    if args.output.is_file():
        data = json.loads(args.output.read_text())
    else:
        data = {
            "schema_version": 1,
            "purpose": (
                "Timestamped public-score readings per submission, so the shape of a "
                "score's trajectory can be measured instead of assumed."
            ),
            "observations": [],
        }
    data["observations"].append({"observed_at_utc": now, "submissions": rows})
    data["last_observed_at_utc"] = now
    data["observation_count"] = len(data["observations"])

    # Per-submission series, newest reading last, for reading at a glance.
    series: dict[str, list] = {}
    for observation in data["observations"]:
        for row in observation["submissions"]:
            if row["public_score"] is None:
                continue
            series.setdefault(str(row["submission_id"]), []).append(
                [observation["observed_at_utc"], row["public_score"]]
            )
    data["series"] = series
    args.output.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    print(f"{now}  observation #{data['observation_count']}")
    for row in rows[:6]:
        score = f"{row['public_score']:.1f}" if row["public_score"] is not None else "-"
        print(f"  {row['submission_id']}  {row['status']:<9} {score:>8}  {row['description'][:44]}")


if __name__ == "__main__":
    main()
