#!/usr/bin/env python3
"""
evaluate_ablation.py — IP2: doprinos pojedine kategorije bodovanja.

Iz punog modela redom uklanja po jednu kategoriju (state, lifestyle, diet,
deficiency, kazne) i mjeri pad rangnih metrika. Kategorija je opravdana ako
njezino uklanjanje pogoršava rezultat (negativan Δ nDCG@k).

Pokretanje:  python evaluate_ablation.py
"""
from __future__ import annotations
import argparse, csv, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics as M
import engine_adapter as E
from evaluate_ranking import eval_method, RESULTS_DIR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--supplements", default=None)
    ap.add_argument("--scenarios", default=None)
    ap.add_argument("--k", type=int, default=5)
    args = ap.parse_args()

    supplements = E.load_supplements(args.supplements)
    scenarios = E.load_scenarios(args.scenarios)
    k = args.k

    base_cfg = E.ScoringConfig()
    base_agg, _ = eval_method(E.rank_full, supplements, scenarios, k, base_cfg)

    ablations = {
        "Puni model": base_cfg,
        "− state_match": base_cfg.clone(enabled={**base_cfg.enabled, "state_match": False}),
        "− lifestyle_match": base_cfg.clone(enabled={**base_cfg.enabled, "lifestyle_match": False}),
        "− diet_match": base_cfg.clone(enabled={**base_cfg.enabled, "diet_match": False}),
        "− deficiency_risk_proxy": base_cfg.clone(enabled={**base_cfg.enabled, "deficiency_risk_proxy": False}),
        "− kazne (penalty)": base_cfg.clone(enabled={**base_cfg.enabled, "penalty": False}),
    }

    print("\n=== IP2: ABLACIJSKA ANALIZA (k = %d) ===" % k)
    print(f"{'Konfiguracija':<26}{'prec@k':>9}{'rec@k':>9}{'nDCG@k':>9}{'MRR':>8}{'Δ nDCG@k':>11}")
    rows = []
    for name, cfg in ablations.items():
        agg, _ = eval_method(E.rank_full, supplements, scenarios, k, cfg)
        d = (agg["ndcg@k"] - base_agg["ndcg@k"]) if agg["ndcg@k"] is not None else None
        d_s = "0 (ref.)" if name == "Puni model" else (f"{d:+.3f}" if d is not None else "—")
        print(f"{name:<26}{agg['precision@k']:>9.3f}{agg['recall@k']:>9.3f}"
              f"{agg['ndcg@k']:>9.3f}{agg['mrr']:>8.3f}{d_s:>11}")
        rows.append([name, agg["precision@k"], agg["recall@k"], agg["ndcg@k"], agg["mrr"], d])

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = os.path.join(RESULTS_DIR, "ablation.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["konfiguracija", "precision@k", "recall@k", "ndcg@k", "mrr", "delta_ndcg"])
        w.writerows(rows)
    print(f"\nCSV zapisan: {out}")


if __name__ == "__main__":
    main()
