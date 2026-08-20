"""
export_supplements.py — izvozi tablicu `supplements` iz PostgreSQL-a u JSON
oblika koji očekuju evaluacijske skripte (vidi data/supplements.sample.json).

    python evaluation/export_supplements.py
    python evaluation/export_supplements.py --out evaluation/data/supplements.json

Pokrenuti nakon svake izmjene u `app/db/seed.py`, jer skripte čitaju izvezeni
JSON, a ne bazu.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.db.database import SessionLocal  # noqa: E402
from app.models.supplement import Supplement  # noqa: E402

DEFAULT_OUT = os.path.join(SCRIPT_DIR, "data", "supplements.json")

FIELDS = (
    "name",
    "nutrient_group",
    "description",
    "goal_tags",
    "state_scores",
    "lifestyle_scores",
    "diet_scores",
    "deficiency_scores",
    "penalties",
)


def export(out_path: str) -> int:
    db = SessionLocal()
    try:
        rows = db.query(Supplement).order_by(Supplement.name).all()
        empty = {"description": "", "nutrient_group": None, "goal_tags": []}
        data = [
            {
                field: (
                    getattr(row, field)
                    if field == "name"
                    else getattr(row, field)
                    or empty.get(field, {} if field.endswith("scores") or field == "penalties" else [])
                )
                for field in FIELDS
            }
            for row in rows
        ]
    finally:
        db.close()

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return len(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()

    count = export(args.out)

    hard = sum(
        1
        for item in json.load(open(args.out, encoding="utf-8"))
        for rule in (item["penalties"] or {}).values()
        if rule.get("hard")
    )
    print(f"Izvezeno {count} dodataka u {args.out} ({hard} tvrdih kontraindikacija).")


if __name__ == "__main__":
    main()
