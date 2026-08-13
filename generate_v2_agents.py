"""Generate thin V2 raw-route agents without modifying V1 agents."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BANK = ROOT / "experiments/v2_route_executor.json"
OUT = ROOT / "agents/super_replay_v2"
INDEX = OUT / "index.json"


def main():
    routes = json.loads(BANK.read_text())["routes"]
    index = {"v1": "agents/super_replay/super_backbone_v1.py"}
    for route in routes:
        route_id = route["route_id"]
        name = "v2_" + route_id.removeprefix("super_")
        path = OUT / f"{name}.py"
        path.write_text(
            '"""V2 elite route with frozen bounded K3 worker weed repair."""\n\n'
            'from runpy import run_path\n\n'
            f'agent = run_path("agents/super_replay_v2/backbone_common.py")["make_agent"]({route_id!r})\n'
        )
        index[name] = str(path.relative_to(ROOT))
    INDEX.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    print(f"generated {len(index)-1} V2 routes")


if __name__ == "__main__":
    main()
