"""Generate thin local agents for complete current Top-50 replay routes."""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parent
BANK = ROOT / "experiments/top50_route_bank.json"
OUT = ROOT / "agents/top50_distilled/raw"


def slug(value):
    return "".join(character if character.isalnum() or character == "_" else "_" for character in value.lower())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    for route in json.loads(BANK.read_text())["routes"]:
        path = OUT / f"{slug(route['route_id'])}.py"
        path.write_text(
            '"""Complete Top-50 replay route with frozen bounded K3 repair."""\n\n'
            'from runpy import run_path\n\n'
            f'agent = run_path("agents/top50_distilled/backbone_common.py")["make_agent"]({route["route_id"]!r})\n'
        )
        index[route["route_id"]] = str(path.relative_to(ROOT))
    (OUT / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    print(f"generated {len(index)} raw Top-50 agents")


if __name__ == "__main__":
    main()
