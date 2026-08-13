"""Generate thin V3 raw-route agents; never modifies V1/V2 agents."""

import json
from pathlib import Path
from runpy import run_path

import package_v27_submission as template


ROOT = Path(__file__).resolve().parent
BANK = ROOT / "experiments/v3_route_executor.json"
OUT = ROOT / "agents/super_replay_v3"
INDEX = OUT / "index.json"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # The standalone package is already proven action-for-action equivalent to
    # the frozen V2 source and avoids loading research route banks in workers.
    index = {"v2": "submission/main.py"}
    for route in json.loads(BANK.read_text())["routes"]:
        name = route["route_id"]
        path = OUT / f"{name}.py"
        template.SOURCE = ROOT / "agents/super_replay_v2/super_backbone_v2.py"
        template.MANIFEST = BANK
        template.OUTPUT = path
        template.EXPECTED_SOURCE_SHA = "c39d82b4f796271603e32ea8cb4b70261fbbe3d4e17940886caf5f5a6bd9adef"
        template.ROUTE_ID = name
        template.main()
        text = path.read_text().replace(
            "Standalone Kaggriculture agent: frozen Victor V27 route + weed repair.",
            "Compact V3 research agent: current Top-10 route + exactly frozen K3 weed repair.",
        ).replace(
            "Generated from agents/v27_replay_weed_guard.py.",
            "Generated from the frozen V2/K3 executor template; research candidate only.",
        )
        path.write_text(text)
        assert run_path(str(path))["agent"].route["route_id"] == name
        index[name] = str(path.relative_to(ROOT))
    INDEX.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    print(f"generated {len(index)-1} V3 raw routes")


if __name__ == "__main__": main()
