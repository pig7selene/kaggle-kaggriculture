"""Build each public notebook's agent into its own file.

Most of these notebooks assemble a complete `main.py` in a cell and then pack it,
but each writes to its own path and several write into the working directory.
Running the code cells inside a scratch directory, with the working directory
moved there, collects whatever agent each one produces without polluting the
repo. The largest Python file a notebook leaves behind is its agent.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, tempfile, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VD = Path("/private/tmp/kaggriculture_v43_variants")


def build(nb: Path, dest: Path) -> dict | None:
    j = json.loads(nb.read_text())
    cells = ["".join(c.get("source", [])) for c in j["cells"] if c["cell_type"] == "code"]
    tmp = Path(tempfile.mkdtemp(prefix="pubnb_"))
    cwd = os.getcwd()
    ns = {}
    pre = (f"from pathlib import Path\nimport os\n"
           f"WORKDIR = Path({str(tmp)!r})\nOUTPUT_ROOT = WORKDIR\nMAIN = WORKDIR / 'main.py'\n")
    try:
        os.chdir(tmp)
        for c in cells:
            try:
                exec(compile(pre + c, "nb", "exec"), ns)
            except SystemExit:
                pass
            except Exception:
                pass
    finally:
        os.chdir(cwd)
    got = sorted(tmp.rglob("*.py"), key=lambda p: -p.stat().st_size)
    got = [p for p in got if p.stat().st_size > 20000]
    if not got:
        shutil.rmtree(tmp, ignore_errors=True)
        return None
    data = got[0].read_bytes()
    dest.write_bytes(data)
    shutil.rmtree(tmp, ignore_errors=True)
    return {"file": dest.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=Path("/private/tmp/kaggriculture_notebooks_0918"))
    a = ap.parse_args()
    receipt = {}
    for nb in sorted(a.dir.glob("*/*.ipynb")):
        tag = nb.parent.name
        dest = VD / f"pub_{tag[:34]}.py"
        try:
            r = build(nb, dest)
        except Exception:
            traceback.print_exc(limit=2)
            r = None
        if r:
            try:
                compile(dest.read_bytes(), "main.py", "exec")
                r["compiles"] = True
            except Exception as exc:
                r["compiles"] = False
                r["error"] = str(exc)[:120]
            receipt[tag] = r
            print(f"  {tag[:44]:44s} -> {dest.name} {r['bytes']:,} bytes compiles={r['compiles']}")
        else:
            print(f"  {tag[:44]:44s} -- no agent produced")
    (ROOT / "experiments" / "public_agents_0918.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
