"""Mechanically embed the promoted opening agent and its dependency graph."""

from __future__ import annotations

import base64
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ENTRYPOINT = "agents/opening_public_front_cow8_day6.py"
SOURCES = (
    "agents/animal_land_common.py",
    "agents/early_compound_common.py",
    "agents/replay_meta_common.py",
    "agents/large_scale_router.py",
    "agents/opening_compound_common.py",
    ENTRYPOINT,
)


def _encoded(path):
    data = (ROOT / path).read_bytes()
    return base64.b85encode(zlib.compress(data, level=9)).decode("ascii")


def _render():
    lines = [
        '"""Standalone Kaggriculture agent: public-compounding opening.',
        "",
        "Generated mechanically from the immutable promoted source dependency graph.",
        "Only Python standard-library modules are imported at runtime.",
        '"""',
        "",
        "import base64 as _base64",
        "import runpy as _runpy",
        "import zlib as _zlib",
        "",
        "",
        "_EMBEDDED_SOURCES = {",
    ]
    for path in SOURCES:
        encoded = _encoded(path)
        lines.append(f"    {path!r}: (")
        for start in range(0, len(encoded), 100):
            lines.append(f"        {encoded[start:start + 100]!r}")
        lines.append("    ),")
    lines.extend(
        [
            "}",
            "",
            "",
            "def _embedded_run_path(path_name, init_globals=None, run_name=None):",
            "    path_name = str(path_name)",
            "    if path_name not in _EMBEDDED_SOURCES:",
            "        raise FileNotFoundError(path_name)",
            "    namespace = dict(init_globals or {})",
            "    namespace.update({",
            "        '__name__': run_name or '<run_path>',",
            "        '__file__': path_name,",
            "        '__cached__': None,",
            "        '__loader__': None,",
            "        '__package__': '',",
            "    })",
            "    compressed = _base64.b85decode(_EMBEDDED_SOURCES[path_name])",
            "    source = _zlib.decompress(compressed).decode('utf-8')",
            "    exec(compile(source, path_name, 'exec'), namespace)",
            "    return namespace",
            "",
            "",
            "_original_run_path = _runpy.run_path",
            "_runpy.run_path = _embedded_run_path",
            "try:",
            f"    agent = _embedded_run_path({ENTRYPOINT!r})['agent']",
            "finally:",
            "    _runpy.run_path = _original_run_path",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    destination = ROOT / "submission" / "main.py"
    destination.write_text(_render())
    print(destination)


if __name__ == "__main__":
    main()
