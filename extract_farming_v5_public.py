"""Extract and hash-verify the exact public Farming Score V5 package."""

from __future__ import annotations

import ast
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


ROOT = Path(__file__).resolve().parent
DEFAULT_NOTEBOOK = ROOT / "experiments/farming_v5_acquisition/farming-score-v5-timing-optimized.ipynb"
DEFAULT_TARGET = ROOT / "agents/public_farming_v5"


def assignment(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            if (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and isinstance(node.value.func.value, ast.Name)
                and node.value.func.value.id == "json"
                and node.value.func.attr == "loads"
            ):
                return json.loads(ast.literal_eval(node.value.args[0]))
            return ast.literal_eval(node.value)
    raise KeyError(name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--notebook", type=Path, default=DEFAULT_NOTEBOOK)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()
    notebook = json.loads(args.notebook.read_text(encoding="utf-8"))
    code = "".join(notebook["cells"][4]["source"])
    tree = ast.parse(code)
    archive_b64 = assignment(tree, "ARCHIVE_B64")
    expected_archive = assignment(tree, "EXPECTED_ARCHIVE_SHA256")
    expected_members = assignment(tree, "EXPECTED_MEMBER_HASHES")

    import base64

    archive = base64.b64decode(archive_b64)
    actual_archive = hashlib.sha256(archive).hexdigest()
    if actual_archive != expected_archive:
        raise ValueError(f"archive hash mismatch: {actual_archive} != {expected_archive}")

    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
        members = {
            member.name: package.extractfile(member).read()
            for member in package.getmembers()
            if member.isfile()
        }
    if set(members) != set(expected_members):
        raise ValueError("archive member set does not match notebook manifest")

    args.target.mkdir(parents=True, exist_ok=True)
    for name, data in members.items():
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError(f"unsafe archive path: {name}")
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected_members[name]:
            raise ValueError(f"member hash mismatch for {name}: {actual}")
        path = args.target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    (args.target / "PUBLIC_ARCHIVE_SHA256.txt").write_text(actual_archive + "\n", encoding="utf-8")
    print(f"verified archive {actual_archive}")
    print(f"extracted {len(members)} exact files to {args.target}")


if __name__ == "__main__":
    main()
