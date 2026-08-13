"""Generate thin research agents for all raw elite route candidates."""

from pathlib import Path
import json


ROOT = Path(__file__).resolve().parent
BANK = ROOT / "experiments/super_replay_route_bank.json"
OUT = ROOT / "agents/super_replay"


def slug(route_id):
    return "".join(character if character.isalnum() or character == "_" else "_" for character in route_id.lower())


def main():
    bank = json.loads(BANK.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    for route in bank["routes"]:
        path = OUT / f"{slug(route['route_id'])}.py"
        path.write_text(
            '"""Elite replay route with the frozen bounded K3 weed repair."""\n\n'
            'from runpy import run_path\n\n'
            f'agent = run_path("agents/super_replay/super_backbone_common.py")["make_super_agent"]({route["route_id"]!r})\n'
        )
        index[route["route_id"]] = str(path.relative_to(ROOT))
    (OUT / "index.json").write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    print(f"generated {len(index)} agents in {OUT}")


if __name__ == "__main__":
    main()
