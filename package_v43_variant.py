"""Package a single-file V43 variant as a deterministic Kaggle submission.

Same archive recipe as every submission in this repository: PAX tar, mtime 0,
uid/gid 0, mode 0644, gzip mtime 0, so the archive hash is a function of the
source alone. The source is also copied to agents/<name>/main.py so the registry
can point at what was actually submitted.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    agent_dir = ROOT / "agents" / args.name
    agent_dir.mkdir(parents=True, exist_ok=True)
    data = args.source.read_bytes()
    compile(data, "main.py", "exec")
    (agent_dir / "main.py").write_bytes(data)

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as tf:
            info = tarfile.TarInfo("main.py")
            info.size, info.mtime, info.uid, info.gid, info.mode = len(data), 0, 0, 0, 0o644
            info.uname = info.gname = ""
            tf.addfile(info, io.BytesIO(data))
    archive = ROOT / "submission" / f"{args.name}.tar.gz"
    archive.write_bytes(buf.getvalue())

    receipt = {
        "name": args.name, "note": args.note,
        "source": str(args.source), "source_sha256": hashlib.sha256(data).hexdigest(),
        "agent_main": str((agent_dir / "main.py").relative_to(ROOT)),
        "archive": str(archive.relative_to(ROOT)), "archive_sha256": sha256(archive),
        "archive_bytes": archive.stat().st_size, "kaggle_submission_made": False,
    }
    (ROOT / "experiments" / f"{args.name}_build.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
