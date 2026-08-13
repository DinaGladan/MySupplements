"""
make_annotation_form.py — priprema listiće za neovisno označavanje (A3).

Ispisuje dvije CSV datoteke:

  data/annotation_form.csv        prazan listić, jedan redak po scenariju
  data/supplement_catalogue.csv   popis svih dodataka s opisom, kao pomoć

Listić NE sadrži izlaz sustava ni pravila bodovanja. To je smisao A3: označivač
prosuđuje relevantnost samostalno, pa se slaganje s tvojim ocjenama može mjeriti
Cohenovom kappom. Ako bi listić pokazivao što sustav predlaže, mjerili bismo
koliko je označivač spreman potvrditi sustav, a ne slaganje dvaju sudova.

Listić ispunjavaju NAJMANJE DVIJE osobe, svaka zasebno, jedna od njih možeš biti
ti. Spremiti kao annotations_<ime>.csv i spojiti s merge_annotations.py.

    python evaluation/make_annotation_form.py
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

from app.db.seed import SUPPLEMENTS_DATA  # noqa: E402

DATA_DIR = os.path.join(SCRIPT_DIR, "data")
SLOTS = 5


def write_catalogue() -> str:
    path = os.path.join(DATA_DIR, "supplement_catalogue.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["naziv", "opis"])
        for item in sorted(SUPPLEMENTS_DATA, key=lambda x: x["name"]):
            writer.writerow([item["name"], item.get("description", "")])
    return path


def write_form(scenarios) -> str:
    path = os.path.join(DATA_DIR, "annotation_form.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(
            ["id", "opis_korisnika", "ciljevi"]
            + [f"relevantan_{i}" for i in range(1, SLOTS + 1)]
        )
        for scenario in scenarios:
            writer.writerow(
                [scenario["id"], scenario["profile_text"], scenario["goals_text"]]
                + [""] * SLOTS
            )
    return path


def main() -> None:
    with open(os.path.join(DATA_DIR, "scenarios.json"), encoding="utf-8") as f:
        scenarios = json.load(f)

    catalogue = write_catalogue()
    form = write_form(scenarios)

    print(f"Zapisano:\n  {form}\n  {catalogue}")
    print(f"\n{len(scenarios)} scenarija, {len(SUPPLEMENTS_DATA)} dodataka, "
          f"{SLOTS} mjesta po scenariju.")
    print("""
Upute za označivača (proslijediti uz listić):

  1. Za svaki redak pročitaj opis korisnika i njegove ciljeve.
  2. Iz popisa u supplement_catalogue.csv odaberi 3 do 5 dodataka koje bi
     preporučio baš toj osobi. Upiši TOČNE nazive iz popisa.
  3. Redoslijed nije važan. Manje od tri upiši samo ako stvarno ne možeš
     opravdati treći.
  4. Ako smatraš da nijedan dodatak nije prikladan, ostavi redak prazan.
  5. Ne konzultiraj se s drugim označivačem i ne gledaj izlaz sustava.

  Spremi kao annotations_<tvoje_ime>.csv u istu mapu.
""")


if __name__ == "__main__":
    main()
