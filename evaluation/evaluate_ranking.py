#!/usr/bin/env python3
"""
evaluate_ranking.py — IP1: kvaliteta rangiranja i usporedba s referentnim metodama.

Za puni model (B3) i tri polazne metode (B0 nasumično, B1 širina/'popularnost',
B2 samo ciljevi) računa precision@5, recall@5, nDCG@5 i MRR na istim scenarijima
i istim (očekivanim) profilima, uz intervale pouzdanosti i Wilcoxonov test
značajnosti punog modela naspram svake polazne metode.

Scenariji s očekivanim praznim rezultatom isključeni su iz rangnih metrika i
prijavljuju se zasebno (točnost praznog slučaja).

Pokretanje:  python evaluate_ranking.py
             python evaluate_ranking.py --supplements data/supplements.sample.json \\
                                        --scenarios data/scenarios.sample.json --k 5
"""
from __future__ import annotations
import argparse, csv, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metrics as M
import engine_adapter as E

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def _profile(scn):
    # koristi očekivani profil kako bi se izolirala logika rangiranja od parsiranja
    return scn.get("expected_profile") or {}


def eval_method(rank_fn, supplements, scenarios, k, cfg, random_seeds=None):
    """Vraća (agregat, per_scenario_ndcg) za jednu metodu."""
    per_p, per_r, per_n, per_mrr, per_hit = [], [], [], [], []
    ndcg_by_id = {}

    ranking_scenarios = [s for s in scenarios if not s.get("expected_empty")]

    for scn in ranking_scenarios:
        rel = set(scn.get("relevant") or [])
        if not rel:
            continue
        if random_seeds:  # prosjek preko sjemena za nasumičnu metodu
            p = r = n = mrr = hit = 0.0
            for sd in random_seeds:
                ranked = E.rank_random(supplements, seed=sd)
                p += M.precision_at_k(ranked, rel, k)
                r += M.recall_at_k(ranked, rel, k)
                n += (M.ndcg_at_k(ranked, rel, k) or 0.0)
                mrr += M.reciprocal_rank(ranked, rel)
                hit += M.hit_at_k(ranked, rel, k)
            m = len(random_seeds)
            p, r, n, mrr, hit = p/m, r/m, n/m, mrr/m, hit/m
        else:
            ranked = rank_fn(supplements, _profile(scn), scn.get("expected_goals"), cfg)
            p = M.precision_at_k(ranked, rel, k)
            r = M.recall_at_k(ranked, rel, k)
            n = M.ndcg_at_k(ranked, rel, k) or 0.0
            mrr = M.reciprocal_rank(ranked, rel)
            hit = M.hit_at_k(ranked, rel, k)
        per_p.append(p); per_r.append(r); per_n.append(n)
        per_mrr.append(mrr); per_hit.append(hit)
        ndcg_by_id[scn["id"]] = n

    n_scn = len(per_hit)
    hits = sum(1 for h in per_hit if h > 0)
    _, hlo, hhi = M.wilson_interval(hits, n_scn)
    agg = {
        "n": n_scn,
        "precision@k": M.mean(per_p),
        "recall@k": M.mean(per_r),
        "recall_hit_rate": hits / n_scn if n_scn else None,
        "recall_hit_ci": (hlo, hhi),
        "ndcg@k": M.mean(per_n),
        "ndcg_ci": M.bootstrap_ci(per_n)[1:],
        "mrr": M.mean(per_mrr),
    }
    return agg, ndcg_by_id


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--supplements", default=None)
    ap.add_argument("--scenarios", default=None)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--random-seeds", type=int, default=20,
                    help="broj sjemena za nasumičnu polaznu metodu")
    args = ap.parse_args()

    supplements = E.load_supplements(args.supplements)
    scenarios = E.load_scenarios(args.scenarios)
    cfg = E.ScoringConfig()
    k = args.k
    seeds = list(range(args.random_seeds))

    methods = {
        "B0 Nasumično": (lambda s, p, g, c: None, {"random_seeds": seeds}),
        "B1 Širina (goal_tags)": (E.rank_breadth, {}),
        "B2 Samo ciljevi": (E.rank_goal_only, {}),
        "B3 Puni model": (E.rank_full, {}),
    }

    results, ndcg_series = {}, {}
    for name, (fn, extra) in methods.items():
        agg, series = eval_method(fn, supplements, scenarios, k, cfg,
                                  random_seeds=extra.get("random_seeds"))
        results[name] = agg
        ndcg_series[name] = series

    # značajnost: puni model vs svaka polazna metoda (uparen Wilcoxon na nDCG@k)
    base = ndcg_series["B3 Puni model"]
    common_ids = list(base.keys())
    sig = {}
    for name in methods:
        if name == "B3 Puni model":
            continue
        x = [base[i] for i in common_ids]
        y = [ndcg_series[name].get(i, 0.0) for i in common_ids]
        sig[name] = M.wilcoxon_signed_rank(x, y)

    # prazan slučaj
    empty_scn = [s for s in scenarios if s.get("expected_empty")]
    empty_ok = 0
    for scn in empty_scn:
        displayed = E.rank_full(supplements, _profile(scn), scn.get("expected_goals"),
                                cfg, respect_threshold=True)
        if len(displayed) == 0:
            empty_ok += 1

    # ---- ispis ----
    print("\n=== IP1: KVALITETA RANGIRANJA (k = %d) ===" % k)
    print(f"{'Metoda':<26}{'prec@k':>9}{'rec@k':>9}{'nDCG@k':>9}{'MRR':>8}"
          f"{'hit-rate (95% CI)':>26}{'p vs B3':>12}")
    for name in methods:
        a = results[name]
        ci = a["recall_hit_ci"]
        ci_s = f"{a['recall_hit_rate']:.2f} [{ci[0]:.2f},{ci[1]:.2f}]" if a["recall_hit_rate"] is not None else "—"
        p_s = "—" if name == "B3 Puni model" else f"{sig[name]['p_value']:.4f}"
        print(f"{name:<26}{a['precision@k']:>9.3f}{a['recall@k']:>9.3f}"
              f"{a['ndcg@k']:>9.3f}{a['mrr']:>8.3f}{ci_s:>26}{p_s:>12}")
    print(f"\nScenariji za rangiranje: n = {results['B3 Puni model']['n']}")
    if empty_scn:
        print(f"Prazan slučaj (expected_empty): {empty_ok}/{len(empty_scn)} ispravno vraćeno prazno")
    print("Napomena: pri malom n Wilcoxon (normalna aproksimacija) je grub; "
          "za konačni rad koristiti n>=15 i po mogućnosti scipy egzaktni način.")

    # ---- CSV ----
    os.makedirs(RESULTS_DIR, exist_ok=True)
    out = os.path.join(RESULTS_DIR, "ranking.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metoda", "n", "precision@k", "recall@k", "recall_hit_rate",
                    "hit_ci_low", "hit_ci_high", "ndcg@k", "ndcg_ci_low",
                    "ndcg_ci_high", "mrr", "p_vs_full"])
        for name in methods:
            a = results[name]
            nci = a["ndcg_ci"]
            w.writerow([name, a["n"], a["precision@k"], a["recall@k"],
                        a["recall_hit_rate"], a["recall_hit_ci"][0], a["recall_hit_ci"][1],
                        a["ndcg@k"], nci[0], nci[1], a["mrr"],
                        "" if name == "B3 Puni model" else sig[name]["p_value"]])
    print(f"\nCSV zapisan: {out}")


if __name__ == "__main__":
    main()
