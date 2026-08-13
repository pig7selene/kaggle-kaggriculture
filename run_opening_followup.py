"""Focused day-8 cow-timing follow-up after the broad opening screen."""

import json

from run_opening_search import ROOT, OPPONENTS, SEEDS, _run, _summary


CANDIDATES = {
    "front_day0_hires": "agents/opening_public_front_hires.py",
    "front_cow7_day7": "agents/opening_public_front_cow7.py",
    "front_cow8_day7": "agents/opening_public_front_cow8.py",
    "front_cow8_day6": "agents/opening_public_front_cow8_day6.py",
}


def main():
    games = []
    jobs = [
        (candidate, str((ROOT / path).resolve()), opponent, str((ROOT / opponent_path).resolve()), seed, seat)
        for candidate, path in CANDIDATES.items()
        for opponent, opponent_path in OPPONENTS.items()
        for seed in SEEDS for seat in (0, 1)
    ]
    for index, job in enumerate(jobs, 1):
        games.append(_run(job))
        if index % 24 == 0:
            print(f"cow timing {index}/{len(jobs)}", flush=True)
    rows = []
    for candidate, path in CANDIDATES.items():
        selected = [game for game in games if game["candidate"] == candidate]
        rows.append({"candidate": candidate, "path": path, "overall": _summary(selected, True)})
    rows.sort(
        key=lambda row: (
            row["overall"]["schedule_success_rate"],
            row["overall"]["average_bank_after_day_10"],
        ),
        reverse=True,
    )
    payload = {
        "schema_version": 1,
        "experiment": "opening_day8_cow_timing_followup",
        "seeds": list(SEEDS),
        "both_seats": True,
        "opponents": OPPONENTS,
        "candidates": rows,
        "games": games,
    }
    output = ROOT / "experiments" / "opening_day8_cow_followup.json"
    output.write_text(json.dumps(payload, indent=2) + "\n")
    print(output)
    for row in rows:
        s = row["overall"]
        print(
            row["candidate"],
            f"template={s['schedule_success_rate']:.1%}",
            f"cows8={s['eight_cows_by_day_8_rate']:.1%}",
            f"bank10={s['average_bank_after_day_10']:.0f}",
            f"tiles10={s['average_productive_tiles_after_day_10']:.1f}",
        )


if __name__ == "__main__":
    main()
