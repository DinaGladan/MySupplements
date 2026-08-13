#!/usr/bin/env python3
"""
evaluate_safety.py — IP3: poštivanje kontraindikacija (SKO) prije i poslije veta.

SKO (stopa kršenja ograničenja) = udio scenarija u kojima se barem jedan
zabranjeni (kontraindicirani) dodatak pojavi u PRIKAZANOM izlazu (prag + top-k).
Uspoređuje meke kazne (oduzimanje, kako je u izvornom sustavu) s tvrdim vetom
(filtriranje prije rangiranja). Cilj revidiranog sustava: SKO = 0%.

Pokretanje:  python evaluate_safety.py
"""
from __future__ import annotations
import argparse, csv, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics as M
import engine_adapter as E

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def sko(supplements, scenarios, cfg):
    """Vraća (broj_krsenja, n, popis_krsenja)."""
    violations, considered = [], []
    for scn in scenarios:
        forbidden = set(scn.get("forbidden") or [])
        if not forbidden:
            continue
        considered.append(scn["id"])
        displayed = set(E.rank_full(supplements, scn.get("expected_profile") or {},
                                    scn.get("expected_goals"), cfg, respect_threshold=True))
        leaked = forbidden & displayed
        if leaked:
            violations.append((scn["id"], sorted(leaked)))
    return len(violations), len(considered), violations


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--supplements", default=None)
    ap.add_argument("--scenarios", default=None)
    args = ap.parse_args()

    supplements = E.load_supplements(args.supplements)
    scenarios = E.load_scenarios(args.scenarios)

    soft = E.ScoringConfig(hard_veto=False)
    veto = E.ScoringConfig(hard_veto=True)

    print("\n=== IP3: POŠTIVANJE KONTRAINDIKACIJA (SKO) ===")
    rows = []
    for label, cfg in [("Meke kazne (oduzimanje)", soft), ("Tvrdi veto", veto)]:
        v, n, details = sko(supplements, scenarios, cfg)
        rate = v / n if n else 0.0
        _, lo, hi = M.wilson_interval(v, n)
        print(f"\n{label}:")
        print(f"  SKO = {v}/{n} = {rate*100:.1f}%   (95% Wilson CI: "
              f"[{lo*100:.1f}%, {hi*100:.1f}%])")
        for sid, leaked in details:
            print(f"    ✗ scenarij {sid}: procurili zabranjeni dodaci: {', '.join(leaked)}")
        if not details:
            print("    ✓ nema kršenja")
        rows.append([label, v, n, rate, lo, hi])

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = os.path.join(RESULTS_DIR, "safety.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["konfiguracija", "krsenja", "n_scenarija", "SKO", "ci_low", "ci_high"])
        w.writerows(rows)
    print(f"\nCSV zapisan: {out}")
    print("Interpretacija: ako meke kazne daju SKO>0, a veto SKO=0, to je izravan "
          "dokaz da kontraindikacije treba tretirati kao tvrdi filtar.")


if __name__ == "__main__":
    main()
