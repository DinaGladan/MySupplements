"""
record_predictions.py — jednom propušta scenarije kroz stvarni parser i zapisuje
izlaz u `predicted_profile` / `predicted_goals` unutar scenarios.json.

Nakon toga `evaluate_nlu.py` radi offline (replay), bez Ollame i bez čekanja.
Bez zapisanih predviđanja replay uspoređuje očekivano s praznim i daje F1 = 0,
što izgleda kao katastrofalan parser, a zapravo znači da podataka nema.

    python evaluation/record_predictions.py                 # izravno kroz app/
    python evaluation/record_predictions.py --api-url http://localhost:8000

Ponoviti nakon svake izmjene prompta, modela ili temperature — inače replay mjeri
staro ponašanje.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

DATA_DIR = os.path.join(SCRIPT_DIR, "data")


def parse_locally(scenario):
    from app.services.goal_parser_service import parse_goals
    from app.services.profile_parser_service import parse_profile

    profile = parse_profile(scenario["profile_text"]).model_dump(mode="json")
    goals = parse_goals(scenario["goals_text"]).goals
    return profile, [g.value if hasattr(g, "value") else g for g in goals]


def parse_over_http(scenario, base_url, timeout):
    import requests

    response = requests.post(
        f"{base_url.rstrip('/')}/parse/full",
        json={
            "profile_text": scenario["profile_text"],
            "goals_text": scenario["goals_text"],
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()

    goals = data.get("goals")
    if isinstance(goals, dict):
        goals = goals.get("goals")

    return data.get("profile") or {}, goals or []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--resume", action="store_true",
                        help="preskoči scenarije koji već imaju zapisano predviđanje")
    args = parser.parse_args()

    path = os.path.join(DATA_DIR, "scenarios.json")
    with open(path, encoding="utf-8") as f:
        scenarios = json.load(f)

    todo = [
        s for s in scenarios
        if not (args.resume and "predicted_profile" in s and "predicted_goals" in s)
    ]
    if args.resume:
        print(f"Nastavak: {len(scenarios) - len(todo)} već zapisano, {len(todo)} preostalo.\n")

    started = time.time()
    for index, scenario in enumerate(todo, 1):
        elapsed = time.time() - started
        rate = elapsed / (index - 1) if index > 1 else 0
        left = f", preostalo ~{rate * (len(todo) - index + 1) / 60:.0f} min" if rate else ""
        print(f"  [{index}/{len(todo)}] {scenario['id']}  ({elapsed:.0f}s{left})", flush=True)

        if args.api_url:
            profile, goals = parse_over_http(scenario, args.api_url, args.timeout)
        else:
            profile, goals = parse_locally(scenario)

        scenario["predicted_profile"] = profile
        scenario["predicted_goals"] = goals

        with open(path, "w", encoding="utf-8") as f:
            json.dump(scenarios, f, ensure_ascii=False, indent=2)

    empty = sum(1 for s in scenarios if not any(v is not None for v in s["predicted_profile"].values()))
    print(f"\nZapisano {len(scenarios)} predviđanja u {path} za {time.time() - started:.0f}s")
    if empty:
        print(f"UPOZORENJE: {empty} scenarija ima potpuno prazan profil — parsiranje je "
              f"vjerojatno isteklo. Provjeri prije nego brojke uđu u rad.")


if __name__ == "__main__":
    main()
