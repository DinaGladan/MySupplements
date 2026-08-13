"""
metrics.py — Metrike i statistika za evaluaciju sustava preporuka.

Implementira rangno-osjetljive metrike (recall@k, precision@k, nDCG@k, MRR),
intervale pouzdanosti (Wilson, normalni, bootstrap), mjere stabilnosti ranga
(overlap@k, Kendallov tau), slaganje označivača (Cohenova/Fleissova kappa) te
Wilcoxonov test predznačenog ranga za usporedbu metoda.

Bez vanjskih ovisnosti (samo standardna knjižnica). Ako je dostupan scipy,
Wilcoxonov test koristi njega; u protivnom se koristi normalna aproksimacija.
"""

from __future__ import annotations
import math
import random as _random
from collections import Counter
from typing import Optional, Sequence

# --------------------------------------------------------------------------- #
# Rangno-osjetljive metrike
# --------------------------------------------------------------------------- #

def _dcg(gains: Sequence[float]) -> float:
    # pozicija p (1-based): diskont = 1 / log2(p + 1); i=0 -> log2(2)
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def ndcg_at_k(ranked_items: Sequence[str], relevant: set, k: int) -> Optional[float]:
    """nDCG@k s binarnom relevantnošću. Vraća None ako nema relevantnih stavki."""
    if not relevant:
        return None
    gains = [1.0 if it in relevant else 0.0 for it in ranked_items[:k]]
    dcg = _dcg(gains)
    idcg = _dcg([1.0] * min(len(relevant), k))
    return dcg / idcg if idcg > 0 else None


def recall_at_k(ranked_items: Sequence[str], relevant: set, k: int) -> Optional[float]:
    if not relevant:
        return None
    hits = sum(1 for it in ranked_items[:k] if it in relevant)
    return hits / len(relevant)


def precision_at_k(ranked_items: Sequence[str], relevant: set, k: int) -> Optional[float]:
    if k <= 0:
        return None
    hits = sum(1 for it in ranked_items[:k] if it in relevant)
    return hits / k


def reciprocal_rank(ranked_items: Sequence[str], relevant: set) -> float:
    for i, it in enumerate(ranked_items):
        if it in relevant:
            return 1.0 / (i + 1)
    return 0.0


def hit_at_k(ranked_items: Sequence[str], relevant: set, k: int) -> float:
    return 1.0 if any(it in relevant for it in ranked_items[:k]) else 0.0


# --------------------------------------------------------------------------- #
# Intervali pouzdanosti
# --------------------------------------------------------------------------- #

def wilson_interval(successes: int, n: int, z: float = 1.96):
    """Wilsonov interval za udio (pouzdan pri malom n i vrijednostima blizu 0/1).
    Vraća (p_hat, donja_granica, gornja_granica)."""
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (p, max(0.0, center - half), min(1.0, center + half))


def mean_ci(values: Sequence[float], z: float = 1.96):
    """Normalni interval pouzdanosti za srednju vrijednost (kontinuirane metrike)."""
    vals = [v for v in values if v is not None]
    n = len(vals)
    if n == 0:
        return (None, None, None)
    m = sum(vals) / n
    if n == 1:
        return (m, m, m)
    var = sum((v - m) ** 2 for v in vals) / (n - 1)
    half = z * math.sqrt(var) / math.sqrt(n)
    return (m, m - half, m + half)


def bootstrap_ci(values: Sequence[float], iters: int = 10000, alpha: float = 0.05, seed: int = 0):
    """Bootstrap interval pouzdanosti za srednju vrijednost (robusno pri malom n)."""
    vals = [v for v in values if v is not None]
    if not vals:
        return (None, None, None)
    rng = _random.Random(seed)
    n = len(vals)
    means = []
    for _ in range(iters):
        means.append(sum(vals[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int((alpha / 2) * iters)]
    hi = means[min(iters - 1, int((1 - alpha / 2) * iters))]
    return (sum(vals) / n, lo, hi)


# --------------------------------------------------------------------------- #
# Stabilnost ranga (za analizu osjetljivosti težina)
# --------------------------------------------------------------------------- #

def overlap_at_k(rank_a: Sequence[str], rank_b: Sequence[str], k: int) -> Optional[float]:
    if k <= 0:
        return None
    return len(set(rank_a[:k]) & set(rank_b[:k])) / k


def kendall_tau(rank_a: Sequence[str], rank_b: Sequence[str]) -> Optional[float]:
    """Kendallov tau nad stavkama zajedničkim objema listama (bez izjednačenja pozicija)."""
    set_b = set(rank_b)
    common = [x for x in rank_a if x in set_b]
    pos_b = {item: i for i, item in enumerate(rank_b)}
    order = [pos_b[x] for x in common]
    n = len(order)
    if n < 2:
        return None
    concordant = discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            if order[j] > order[i]:
                concordant += 1
            elif order[j] < order[i]:
                discordant += 1
    total = concordant + discordant
    return (concordant - discordant) / total if total else None


# --------------------------------------------------------------------------- #
# Slaganje označivača
# --------------------------------------------------------------------------- #

def cohen_kappa(labels_a: Sequence[int], labels_b: Sequence[int]) -> Optional[float]:
    """Cohenova kappa za dva označivača, binarne oznake (0/1) poravnate po stavci."""
    n = len(labels_a)
    if n == 0 or n != len(labels_b):
        return None
    po = sum(1 for a, b in zip(labels_a, labels_b) if a == b) / n
    pa1 = sum(labels_a) / n
    pb1 = sum(labels_b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def fleiss_kappa(count_matrix: Sequence[Sequence[int]]) -> Optional[float]:
    """Fleissova kappa za >=3 označivača.
    count_matrix[i] = [broj glasova za kategoriju 0, za kategoriju 1, ...],
    svaki redak mora imati isti zbroj (broj označivača R)."""
    N = len(count_matrix)
    if N == 0:
        return None
    R = sum(count_matrix[0])
    if R < 2:
        return None
    k = len(count_matrix[0])
    P = [(sum(c * (c - 1) for c in row)) / (R * (R - 1)) for row in count_matrix]
    Pbar = sum(P) / N
    pj = [sum(row[j] for row in count_matrix) / (N * R) for j in range(k)]
    Pe = sum(p * p for p in pj)
    return 1.0 if Pe == 1 else (Pbar - Pe) / (1 - Pe)


# --------------------------------------------------------------------------- #
# Test značajnosti (uparena usporedba metoda)
# --------------------------------------------------------------------------- #

def _norm_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2))


def wilcoxon_signed_rank(x: Sequence[float], y: Sequence[float]) -> dict:
    """Wilcoxonov test predznačenog ranga (uparen, dvosmjeran).
    Koristi scipy ako je dostupan; inače normalnu aproksimaciju s korekcijom veza.
    Napomena: za vrlo mali n (< ~10) normalna aproksimacija je gruba — poželjno je
    tada koristiti egzaktnu tablicu (npr. scipy `mode='exact'`)."""
    try:
        from scipy.stats import wilcoxon  # type: ignore
        stat, p = wilcoxon(list(x), list(y), zero_method="wilcox",
                           correction=True, alternative="two-sided")
        return {"statistic": float(stat), "p_value": float(p), "method": "scipy"}
    except Exception:
        pass

    diffs = [a - b for a, b in zip(x, y) if (a - b) != 0]
    n = len(diffs)
    if n == 0:
        return {"statistic": 0.0, "p_value": 1.0, "method": "svi_parovi_jednaki", "n": 0}

    indexed = sorted(range(n), key=lambda i: abs(diffs[i]))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(diffs[indexed[j + 1]]) == abs(diffs[indexed[i]]):
            j += 1
        avg = (i + 1 + j + 1) / 2.0
        for t in range(i, j + 1):
            ranks[indexed[t]] = avg
        i = j + 1

    w_pos = sum(ranks[i] for i in range(n) if diffs[i] > 0)
    w_neg = sum(ranks[i] for i in range(n) if diffs[i] < 0)
    T = min(w_pos, w_neg)
    mean = n * (n + 1) / 4.0
    tie_term = sum(t ** 3 - t for t in Counter(abs(d) for d in diffs).values())
    var = (n * (n + 1) * (2 * n + 1)) / 24.0 - tie_term / 48.0
    if var <= 0:
        return {"statistic": T, "p_value": 1.0, "method": "normal-approx", "n": n}
    z = (T - mean) / math.sqrt(var)
    p = min(1.0, 2 * _norm_sf(abs(z)))
    return {"statistic": T, "p_value": p, "method": "normal-approx", "z": z, "n": n}


# --------------------------------------------------------------------------- #
# Pomoćno
# --------------------------------------------------------------------------- #

def percentile(values: Sequence[float], p: float) -> Optional[float]:
    """Linearno interpolirani percentil (p u [0, 100])."""
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    k = (len(vals) - 1) * p / 100.0
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return vals[int(k)]
    return vals[f] + (vals[c] - vals[f]) * (k - f)


def mean(values: Sequence[float]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None
