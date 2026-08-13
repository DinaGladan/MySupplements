#!/usr/bin/env python3
"""
run_all.py — Pokreće sve offline evaluacije redom (rangiranje, ablacija,
osjetljivost, sigurnost, NLU-replay, performanse-engine) i sprema CSV izvještaje
u results/. Za e2e i uživo mjerenja pokrenite pojedine skripte s --api-url.

Pokretanje:  python run_all.py
"""
from __future__ import annotations
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import evaluate_ranking
import evaluate_ablation
import evaluate_sensitivity
import evaluate_safety
import evaluate_nlu
import evaluate_performance


_SKIPPED = []


def _run(name, fn):
    print("\n" + "=" * 70)
    print(f">>> {name}")
    print("=" * 70)
    old = sys.argv
    sys.argv = [name]          # pokreni sa zadanim argumentima
    try:
        fn()
    except SystemExit as e:
        # Skripta se sama zaustavila jer joj nedostaju podaci (npr. oznake
        # relevantnosti). To nije razlog da stanu i ostale evaluacije.
        if e.code not in (0, None):
            print(e.code)
        _SKIPPED.append(name)
    finally:
        sys.argv = old


def main():
    _run("evaluate_ranking", evaluate_ranking.main)
    _run("evaluate_ablation", evaluate_ablation.main)
    _run("evaluate_sensitivity", evaluate_sensitivity.main)
    _run("evaluate_safety", evaluate_safety.main)
    _run("evaluate_nlu", evaluate_nlu.main)
    _run("evaluate_performance", evaluate_performance.main)
    print("\nGotovo. CSV izvještaji su u mapi results/.")
    if _SKIPPED:
        print(f"Preskočeno jer nedostaju podaci: {', '.join(_SKIPPED)}")


if __name__ == "__main__":
    main()
