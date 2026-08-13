#!/usr/bin/env python3
"""
evaluate_sensitivity.py — Analiza osjetljivosti težina.

Perturbira svaku težinu (i prag prikaza) za ±Δ te mjeri stabilnost prvih k
preporuka u odnosu na nezmijenjenu konfiguraciju:
  - overlap@k (udio zajedničkih stavki u top-k)
  - Kendallov tau (podudarnost poretka)
  - Δ nDCG@k

Visok overlap@k (npr. >0.8) i tau blizu 1 znače da preporuke nisu artefakt
točno odabranih brojeva.

Pokretanje:  python evaluate_sensitivity.py --delta 1
"""
from __future__ import annotations
import argparse, csv, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics as M
import engine_adapter as E

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def _profile(scn):
    return scn.get("expected_profile") or {}


def _ranked_thresholded(supplements, scn, cfg):
    # ranking kakav vidi korisnik (prag + top-k)
    return E.rank_full(supplements, _profile(scn), scn.get("expected_goals"),
                       cfg, respect_threshold=True)


def _ndcg(supplements, scn, cfg, k):
    rel = set(scn.get("relevant") or [])
    if not rel:
        return None
    ranked = E.rank_full(supplements, _profile(scn), scn.get("expected_goals"), cfg,
                         respect_threshold=False)
    return M.ndcg_at_k(ranked, rel, k)


def perturbations(base: E.ScoringConfig, delta: float):
    cs = base.category_scale
    return {
        f"goal_weight {base.goal_weight:+g}{delta:+g}": base.clone(goal_weight=base.goal_weight + delta),
        f"goal_weight {base.goal_weight:+g}{-delta:+g}": base.clone(goal_weight=max(0, base.goal_weight - delta)),
        "state_scale +unit": base.clone(category_scale={**cs, "state_match": cs["state_match"] + delta / 2}),
        "state_scale -unit": base.clone(category_scale={**cs, "state_match": max(0, cs["state_match"] - delta / 2)}),
        "penalty_scale +unit": base.clone(penalty_scale=base.penalty_scale + delta / 2),
        "penalty_scale -unit": base.clone(penalty_scale=max(0, base.penalty_scale - delta / 2)),
        f"MIN_DISPLAY_SCORE {delta:+g}": base.clone(min_display_score=base.min_display_score + delta),
        f"MIN_DISPLAY_SCORE {-delta:+g}": base.clone(min_display_score=max(0, base.min_display_score - delta)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--supplements", default=None)
    ap.add_argument("--scenarios", default=None)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--delta", type=float, default=1.0)
    args = ap.parse_args()

    supplements = E.load_supplements(args.supplements)
    scenarios = [s for s in E.load_scenarios(args.scenarios) if not s.get("expected_empty")]
    E.require_relevance_labels(scenarios, "evaluate_sensitivity.py")
    k = args.k
    base = E.ScoringConfig()

    base_top = {s["id"]: _ranked_thresholded(supplements, s, base) for s in scenarios}
    base_ndcg = {s["id"]: _ndcg(supplements, s, base, k) for s in scenarios}

    print("\n=== ANALIZA OSJETLJIVOSTI TEŽINA (k = %d, Δ = %g) ===" % (k, args.delta))
    print(f"{'Perturbacija':<28}{'overlap@k':>11}{'Kendall τ':>11}{'Δ nDCG@k':>11}")
    rows = []
    for name, cfg in perturbations(base, args.delta).items():
        ov, taus, dnd = [], [], []
        for s in scenarios:
            new_top = _ranked_thresholded(supplements, s, cfg)
            o = M.overlap_at_k(base_top[s["id"]], new_top, k)
            t = M.kendall_tau(base_top[s["id"]], new_top)
            if o is not None: ov.append(o)
            if t is not None: taus.append(t)
            b, n = base_ndcg[s["id"]], _ndcg(supplements, s, cfg, k)
            if b is not None and n is not None: dnd.append(n - b)
        mo, mt, md = M.mean(ov), M.mean(taus), M.mean(dnd)
        print(f"{name:<28}{(mo if mo is not None else 0):>11.3f}"
              f"{(mt if mt is not None else float('nan')):>11.3f}"
              f"{(md if md is not None else 0):>11.3f}")
        rows.append([name, mo, mt, md])

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = os.path.join(RESULTS_DIR, "sensitivity.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["perturbacija", "overlap@k", "kendall_tau", "delta_ndcg"])
        w.writerows(rows)
    print(f"\nCSV zapisan: {out}")


if __name__ == "__main__":
    main()
