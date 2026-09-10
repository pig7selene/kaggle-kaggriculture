"""Reconstruct read-only public Kaggriculture agents from retained notebooks.

This utility writes only to a caller-supplied temporary directory.  It does not
touch the frozen research or submission artifacts.
"""

from __future__ import annotations

import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import zlib


SOURCE_ROOT = Path("/private/tmp/kag_frontier_U1u2mf")


def cell_source(notebook: Path, index: int) -> str:
    cell = json.loads(notebook.read_text())["cells"][index]["source"]
    return "".join(cell) if isinstance(cell, list) else cell


def literal_assignment(source: str, name: str):
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def safe_write(root: Path, name: str, data: bytes) -> None:
    target = (root / name).resolve()
    if target.parent != root.resolve():
        raise ValueError(f"unsafe member: {name}")
    target.write_bytes(data)


def extract_embedded_archive(notebook: Path, cell: int, root: Path) -> dict:
    source = cell_source(notebook, cell)
    archive = base64.b64decode(literal_assignment(source, "ARCHIVE_B64"), validate=True)
    expected_archive = literal_assignment(source, "EXPECTED_ARCHIVE_SHA256")
    expected_members = literal_assignment(source, "EXPECTED_MEMBER_SHA256")
    assert hashlib.sha256(archive).hexdigest() == expected_archive
    archive_path = root / "source_submission.tar.gz"
    archive_path.write_bytes(archive)
    with tarfile.open(archive_path, "r:gz") as handle:
        for member in handle.getmembers():
            if not member.isfile() or member.name not in expected_members:
                raise ValueError(f"unexpected member: {member.name}")
            data = handle.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest() == expected_members[member.name]
            safe_write(root, member.name, data)
    return {"archive_sha256": expected_archive, "member_sha256": expected_members}


def extract_writefile_agent(notebook: Path, root: Path) -> dict:
    payload = json.loads(notebook.read_text())
    hashes = {}
    for cell in payload["cells"]:
        source = cell["source"]
        source = "".join(source) if isinstance(source, list) else source
        if not source.startswith("%%writefile "):
            continue
        first, body = source.split("\n", 1)
        name = first.split(maxsplit=1)[1].strip()
        safe_write(root, name, body.encode())
        hashes[name] = hashlib.sha256(body.encode()).hexdigest()

    settings_source = next(
        ("".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"])
        for cell in payload["cells"]
        if ("".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]).startswith("SETTINGS =")
    )
    settings = literal_assignment(settings_source, "SETTINGS")
    settings_bytes = (json.dumps(settings, indent=2, sort_keys=True) + "\n").encode()
    safe_write(root, "settings.json", settings_bytes)
    hashes["settings.json"] = hashlib.sha256(settings_bytes).hexdigest()

    route_source = next(
        ("".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"])
        for cell in payload["cells"]
        if "ROUTE_DATA =" in ("".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"])
    )
    actions = gzip.decompress(base64.b64decode(literal_assignment(route_source, "ROUTE_DATA"), validate=True))
    safe_write(root, "actions.json", actions)
    hashes["actions.json"] = hashlib.sha256(actions).hexdigest()
    return {"member_sha256": hashes}


def extract_structured(notebook: Path, root: Path) -> dict:
    payload = json.loads(notebook.read_text())
    main_source = cell_source(notebook, 4)
    _, main_body = main_source.split("\n", 1)
    safe_write(root, "main.py", main_body.encode())
    data_source = cell_source(notebook, 5)
    data = json.loads(gzip.decompress(base64.b64decode(literal_assignment(data_source, "data_payload"))))
    for name, content in data.items():
        safe_write(root, name, content.encode())
    return {
        "member_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.iterdir()
            if path.is_file()
        }
    }


def extract_zlib_archive(notebook: Path, root: Path) -> dict:
    payload = json.loads(notebook.read_text())
    source = next(
        ("".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"])
        for cell in payload["cells"]
        if cell["cell_type"] == "code"
    )
    archive = zlib.decompress(base64.b64decode(literal_assignment(source, "PAYLOAD")))
    expected = literal_assignment(source, "EXPECTED_ARCHIVE_SHA")
    assert hashlib.sha256(archive).hexdigest() == expected
    archive_path = root / "source_submission.tar.gz"
    archive_path.write_bytes(archive)
    members = {}
    with tarfile.open(archive_path, "r:gz") as handle:
        for member in handle.getmembers():
            if not member.isfile():
                continue
            data = handle.extractfile(member).read()
            safe_write(root, member.name, data)
            members[member.name] = hashlib.sha256(data).hexdigest()
    return {"archive_sha256": expected, "member_sha256": members}


def extract_zlib_source(notebook: Path, root: Path) -> dict:
    payload = json.loads(notebook.read_text())
    source_cell = next(
        ("".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"])
        for cell in payload["cells"]
        if cell["cell_type"] == "code"
    )
    source = zlib.decompress(base64.b64decode(literal_assignment(source_cell, "PAYLOAD")))
    expected = literal_assignment(source_cell, "EXPECTED_SOURCE_SHA256")
    assert hashlib.sha256(source).hexdigest() == expected
    safe_write(root, "main.py", source)
    return {"member_sha256": {"main.py": expected}}


def extract_base64_source(notebook: Path, root: Path) -> dict:
    payload = json.loads(notebook.read_text())
    source_cell = next(
        ("".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"])
        for cell in payload["cells"]
        if cell["cell_type"] == "code" and "MAIN_B64" in (
            "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
        )
    )
    source = base64.b64decode(literal_assignment(source_cell, "MAIN_B64"), validate=True)
    expected = literal_assignment(source_cell, "EXPECTED_MAIN_SHA256")
    assert hashlib.sha256(source).hexdigest() == expected
    safe_write(root, "main.py", source)
    return {"member_sha256": {"main.py": expected}}


def main() -> None:
    destination = Path(sys.argv[1]).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    specs = {
        "market_smart": (
            SOURCE_ROOT / "market_smart/market-smart-farming-kaggriculture.ipynb",
            lambda source, root: extract_embedded_archive(source, 9, root),
        ),
        "most_powerfull": (
            SOURCE_ROOT / "most_powerfull/kaggriculture-most-powerfull-route.ipynb",
            extract_writefile_agent,
        ),
        "seven_rescue": (
            SOURCE_ROOT / "seven_rescue/kaggriculture-seven-turn-rescue-best-lb-2800.ipynb",
            extract_writefile_agent,
        ),
        "structured_v2": (
            SOURCE_ROOT / "structured_v2/kaggriculture-structured-economic-policy-v2.ipynb",
            extract_structured,
        ),
        "adaptive_v2": (
            Path("/private/tmp/lb_gap_adaptive_v2/adaptive-route-agent-v2.ipynb"),
            extract_zlib_archive,
        ),
        "farming_v3_current": (
            Path("/private/tmp/lb_gap_farming_v3/farming-score-v3-replay-revised.ipynb"),
            extract_zlib_source,
        ),
        "shape_shop_current": (
            Path("/private/tmp/lb_gap_shape_shop/shape-the-shop-work-the-pasture-kaggriculture.ipynb"),
            extract_base64_source,
        ),
    }
    manifest = {}
    for name, (source, extractor) in specs.items():
        root = destination / name
        root.mkdir(parents=True, exist_ok=True)
        result = extractor(source, root)
        result["notebook"] = str(source)
        result["notebook_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        manifest[name] = result
    (destination / "extraction_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
