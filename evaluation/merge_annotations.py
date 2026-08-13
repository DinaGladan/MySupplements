"""
merge_annotations.py — spaja ispunjene listiće u scenarios.json i računa kappu.

    python evaluation/merge_annotations.py data/annotations_dina.csv data/annotations_ivan.csv

Radi tri stvari:

  1. Provjerava upisane nazive. Tipfeler u nazivu tiho bi izgubio jednu oznaku i
     pokvario i kappu i mjere rangiranja, pa se odbija odmah i glasno.
  2. Računa Cohenovu kappu (dva označivača) ili Fleissovu (tri i više) nad
     binarnim oznakama relevantnosti po paru scenarij-dodatak.
  3. Upisuje `relevant` u scenarios.json kao dodatke koje je označila VEĆINA
     označivača; kod dva označivača to znači presjek.

Zašto većina, a ne unija: unija bi napuhala broj relevantnih stavki i vratila
recall@5 u zasićenje, što je upravo problem na koji recenzija upozorava.
"""

from __future__ import annotations

import csv
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from app.db.seed import SUPPLEMENTS_DATA  # noqa: E402
from metrics import cohen_kappa, fleiss_kappa  # noqa: E402

DATA_DIR = os.path.join(SCRIPT_DIR, "data")
VALID_NAMES = {item["name"] for item in SUPPLEMENTS_DATA}


def read_annotations(path: str) -> dict[str, set[str]]:
    labels: dict[str, set[str]] = {}
    problems: list[str] = []

    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            sid = (row.get("id") or "").strip()
            if not sid:
                continue
            picked = set()
            for key, value in row.items():
                if not key or not key.startswith("relevantan_"):
                    continue
                name = (value or "").strip()
                if not name:
                    continue
                if name not in VALID_NAMES:
                    problems.append(f"{sid}: nepoznat naziv {name!r}")
                    continue
                picked.add(name)
            labels[sid] = picked

    if problems:
        raise SystemExit(
            f"\n{os.path.basename(path)} — neispravni nazivi:\n  "
            + "\n  ".join(problems)
            + "\n\nIspravi ih prema data/supplement_catalogue.csv i pokreni ponovno."
        )

    return labels


def main() -> None:
    paths = sys.argv[1:]
    if len(paths) < 2:
        raise SystemExit(
            "Potrebna su najmanje dva ispunjena listića (kappa mjeri slaganje).\n"
            "  python evaluation/merge_annotations.py data/annotations_a.csv data/annotations_b.csv"
        )

    annotators = [read_annotations(p) for p in paths]

    scenarios_path = os.path.join(DATA_DIR, "scenarios.json")
    with open(scenarios_path, encoding="utf-8") as f:
        scenarios = json.load(f)

    ids = [s["id"] for s in scenarios]
    missing = [
        os.path.basename(path)
        for path, labels in zip(paths, annotators)
        if set(ids) - set(labels)
    ]
    if missing:
        raise SystemExit(f"Listići nemaju sve scenarije: {missing}")

    names = sorted(VALID_NAMES)
    per_annotator = [
        [1 if name in labels[sid] else 0 for sid in ids for name in names]
        for labels in annotators
    ]

    if len(annotators) == 2:
        kappa = cohen_kappa(per_annotator[0], per_annotator[1])
        kind = "Cohenova"
    else:
        matrix = [
            [sum(1 for a in per_annotator if a[i] == 0),
             sum(1 for a in per_annotator if a[i] == 1)]
            for i in range(len(per_annotator[0]))
        ]
        kappa = fleiss_kappa(matrix)
        kind = "Fleissova"

    threshold = len(annotators) / 2
    counts = []
    for scenario in scenarios:
        sid = scenario["id"]
        agreed = sorted(
            name for name in names
            if sum(1 for labels in annotators if name in labels[sid]) > threshold
        )
        scenario["relevant"] = agreed
        counts.append(len(agreed))

    with open(scenarios_path, "w", encoding="utf-8") as f:
        json.dump(scenarios, f, ensure_ascii=False, indent=2)

    print(f"Označivača: {len(annotators)}")
    print(f"{kind} kappa = {kappa:.3f}" if kappa is not None else "kappa: nedostupna")
    print(f"Prosječno relevantnih po scenariju: {sum(counts) / len(counts):.1f}")
    print(f"Scenarija bez ijednog relevantnog: {sum(1 for c in counts if c == 0)}")
    if sum(counts) / len(counts) < 3:
        print("\nUPOZORENJE: prosjek je ispod 3. Popis (A2.1) traži 3-5 relevantnih po\n"
              "scenariju, inače recall@5 ostaje trivijalno zasićen.")
    print(f"\nUpisano u {scenarios_path}")


if __name__ == "__main__":
    main()
