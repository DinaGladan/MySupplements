"""
engine_adapter.py — Referentna implementacija mehanizma bodovanja i rangiranja.

Vjerno replicira logiku iz poglavlja 7 rada (šest kategorija, aditivno
bodovanje, kazne, prag prikaza, top-k, oznake snage). Težine su parametrizirane
(ScoringConfig) kako bi se mogle izvoditi ablacija, analiza osjetljivosti i
usporedba s tvrdim vetom.

VAŽNO — spajanje na stvarni sustav:
    Ako želite vrednovati SVOJ stvarni mehanizam umjesto ove referentne
    implementacije, zamijenite funkciju `rank_full` (i po potrebi `recommend`)
    pozivom vlastitog `recommendation_engine`. Sučelje koje evaluacijske skripte
    očekuju jest:  funkcija(supplements, profile, goals, cfg) -> List[str]
    (uređena lista naziva dodataka). Sve ostalo (metrike, testovi) ostaje isto.
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from typing import List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

# Kategorije koje se zbrajaju u pozitivni dio rezultata (usklađeno s poglavljem 7)
POSITIVE_CATEGORIES = [
    "goal_match", "state_match", "lifestyle_match",
    "diet_match", "deficiency_risk_proxy",
]

# Mapiranje kategorija na stupce baze znanja
_CATEGORY_TO_COLUMN = {
    "state_match": "state_scores",
    "lifestyle_match": "lifestyle_scores",
    "diet_match": "diet_scores",
    "deficiency_risk_proxy": "deficiency_scores",
}


@dataclass
class ScoringConfig:
    """Parametri bodovanja. Zadane vrijednosti odgovaraju sustavu iz rada."""
    goal_weight: float = 2.0                     # bodovi po podudarnom cilju
    category_scale: dict = field(default_factory=lambda: {
        "state_match": 1.0, "lifestyle_match": 1.0,
        "diet_match": 1.0, "deficiency_risk_proxy": 1.0,
    })
    penalty_scale: float = 1.0                    # množitelj kazni
    enabled: dict = field(default_factory=lambda: {
        "goal_match": True, "state_match": True, "lifestyle_match": True,
        "diet_match": True, "deficiency_risk_proxy": True, "penalty": True,
    })
    min_display_score: float = 4.0                # MIN_DISPLAY_SCORE
    top_k: int = 5
    hard_veto: bool = False                       # True -> kontraindikacija = tvrdi filtar
    strength_very_relevant: float = 7.0
    strength_good: float = 5.0

    def clone(self, **overrides) -> "ScoringConfig":
        import copy
        c = copy.deepcopy(self)
        for key, val in overrides.items():
            setattr(c, key, val)
        return c


# --------------------------------------------------------------------------- #
# Izgradnja tokena iz profila
# --------------------------------------------------------------------------- #

def profile_to_tokens(profile: dict) -> set:
    """Svako ne-null polje profila -> token 'field:value'. Null polja se preskaču."""
    tokens = set()
    for name, value in (profile or {}).items():
        if value is None:
            continue
        if isinstance(value, bool):
            tokens.add(f"{name}:{'true' if value else 'false'}")
        else:
            tokens.add(f"{name}:{value}")
    return tokens


# --------------------------------------------------------------------------- #
# Bodovanje jednog dodatka
# --------------------------------------------------------------------------- #

def score_supplement(supp: dict, tokens: set, goals, cfg: ScoringConfig) -> dict:
    goal_set = set(goals or [])
    goal_tags = set(supp.get("goal_tags") or [])
    breakdown = {c: 0.0 for c in POSITIVE_CATEGORIES}

    if cfg.enabled.get("goal_match", True):
        breakdown["goal_match"] = cfg.goal_weight * len(goal_set & goal_tags)

    for cat, column in _CATEGORY_TO_COLUMN.items():
        if not cfg.enabled.get(cat, True):
            continue
        scores = supp.get(column) or {}
        raw = sum(v for tok, v in scores.items() if tok in tokens)
        breakdown[cat] = cfg.category_scale.get(cat, 1.0) * raw

    penalty_risk = 0.0
    warnings: List[str] = []
    vetoed = False
    for tok, rule in (supp.get("penalties") or {}).items():
        if tok in tokens:
            vetoed = True
            penalty_risk += rule.get("penalty", 0)
            if rule.get("warning"):
                warnings.append(rule["warning"])
    if not cfg.enabled.get("penalty", True):
        penalty_risk = 0.0
    else:
        penalty_risk *= cfg.penalty_scale

    total = sum(breakdown.values()) - penalty_risk
    return {
        "name": supp["name"], "total": total, "breakdown": breakdown,
        "penalty_risk": penalty_risk, "warnings": warnings, "vetoed": vetoed,
    }


def strength_label(total: float, cfg: ScoringConfig) -> str:
    if total >= cfg.strength_very_relevant:
        return "very_relevant"
    if total >= cfg.strength_good:
        return "good"
    return "weak"


# --------------------------------------------------------------------------- #
# Rangiranje
# --------------------------------------------------------------------------- #

def recommend(supplements, profile, goals, cfg: ScoringConfig,
              respect_threshold: bool = True) -> List[dict]:
    """Puni tijek: bodovanje -> (veto) -> sortiranje -> (prag) -> top-k.
    Vraća listu bodovnih zapisa (dict). Redoslijed je deterministički (ime kao
    sekundarni ključ)."""
    tokens = profile_to_tokens(profile)
    scored = [score_supplement(s, tokens, goals, cfg) for s in supplements]
    if cfg.hard_veto:
        scored = [r for r in scored if not r["vetoed"]]
    scored.sort(key=lambda r: (-r["total"], r["name"]))
    if respect_threshold:
        scored = [r for r in scored if r["total"] >= cfg.min_display_score]
    return scored[:cfg.top_k] if cfg.top_k else scored


# --------------------------------------------------------------------------- #
# Rangeri (jedno sučelje: -> List[str] naziva)
# --------------------------------------------------------------------------- #

def rank_reference(supplements, profile, goals, cfg: ScoringConfig,
                   respect_threshold: bool = False) -> List[str]:
    """Referentna implementacija poglavlja 7 (izvorni `rank_full` iz paketa).
    Zadržana radi usporedbe sa stvarnim mehanizmom."""
    return [r["name"] for r in recommend(supplements, profile, goals, cfg,
                                         respect_threshold=respect_threshold)]


def rank_full(supplements, profile, goals, cfg: ScoringConfig,
              respect_threshold: bool = False) -> List[str]:
    """Puni model — poziva STVARNI mehanizam iz `app/` (vidi real_engine.py).

    Za usporedbu kvalitete rangiranja koristi se respect_threshold=False
    (rangira sve dodatke); za ponašanje kakvo vidi korisnik koristi se True.

    Postavljanjem EVAL_ENGINE=reference vraća se na referentnu implementaciju,
    što služi samo za provjeru da se dvije izvedbe slažu."""
    if os.environ.get("EVAL_ENGINE", "real").lower() == "reference":
        return rank_reference(supplements, profile, goals, cfg,
                              respect_threshold=respect_threshold)

    from real_engine import rank_real
    return rank_real(supplements, profile, goals, cfg,
                     respect_threshold=respect_threshold)


def rank_goal_only(supplements, profile, goals, cfg: ScoringConfig) -> List[str]:
    """Referentna metoda B2: rangira samo po podudaranju ciljeva."""
    goal_set = set(goals or [])
    scored = [(s["name"], cfg.goal_weight * len(goal_set & set(s.get("goal_tags") or [])))
              for s in supplements]
    scored.sort(key=lambda x: (-x[1], x[0]))
    return [n for n, _ in scored]


def rank_breadth(supplements, profile, goals, cfg: ScoringConfig) -> List[str]:
    """Referentna metoda B1 ('popularnost'/širina): rangira po broju goal_tags.
    Namjerno izlaže pristranost širine — puni model treba ju nadmašiti."""
    scored = [(s["name"], len(s.get("goal_tags") or [])) for s in supplements]
    scored.sort(key=lambda x: (-x[1], x[0]))
    return [n for n, _ in scored]


def rank_random(supplements, seed: int = 0) -> List[str]:
    """Referentna metoda B0: nasumičan poredak (za dano sjeme)."""
    import random
    names = [s["name"] for s in supplements]
    random.Random(seed).shuffle(names)
    return names


# --------------------------------------------------------------------------- #
# Učitavanje podataka
# --------------------------------------------------------------------------- #

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _default_path(real_name: str, sample_name: str) -> str:
    """Stvarni podaci ako postoje, inače priloženi predložak.

    Bez ovoga run_all.py uvijek čita predloške s pet primjera, jer pojedinim
    skriptama ne prosljeđuje argumente, pa bi se lako dogodilo da u rad uđu
    brojevi dobiveni na uzorku."""
    real_path = os.path.join(DATA_DIR, real_name)
    return real_path if os.path.exists(real_path) else os.path.join(DATA_DIR, sample_name)


def load_supplements(path: Optional[str] = None) -> List[dict]:
    """Učitava bazu znanja o dodacima. Za stvarnu evaluaciju izvezite svoju
    PostgreSQL tablicu `supplements` skriptom export_supplements.py."""
    return load_json(path or _default_path("supplements.json", "supplements.sample.json"))


def load_scenarios(path: Optional[str] = None) -> List[dict]:
    return load_json(path or _default_path("scenarios.json", "scenarios.sample.json"))


def require_relevance_labels(scenarios: List[dict], script: str) -> None:
    """Prekini s razumljivom porukom ako oznake relevantnosti još ne postoje.

    Mjere rangiranja su nedefinirane bez njih, pa bi skripta inače pukla usred
    ispisa tablice na nečitljivoj grešci o tipu."""
    if any(s.get("relevant") for s in scenarios):
        return

    # Ukloni raniji izvještaj ove skripte. Kad bi ostao, u results/ bi stajala
    # tablica s brojevima iz nekog prijašnjeg pokretanja, a ništa je ne bi
    # označilo kao zastarjelu.
    stale = os.path.join(SCRIPT_DIR, "results", script.replace("evaluate_", "").replace(".py", "") + ".csv")
    if os.path.exists(stale):
        os.remove(stale)

    raise SystemExit(
        f"\n{script}: nijedan scenarij nema popunjeno polje `relevant`.\n\n"
        "Mjere rangiranja se bez oznaka relevantnosti ne mogu izračunati. Te oznake\n"
        "daju neovisni označivači (stavka A3), a ne sustav — inače bi se sustav\n"
        "ocjenjivao vlastitim pravilima.\n\n"
        "Postupak:\n"
        "  1. python evaluation/make_annotation_form.py\n"
        "  2. dvije osobe zasebno ispune data/annotation_form.csv\n"
        "  3. python evaluation/merge_annotations.py data/annotations_a.csv data/annotations_b.csv\n\n"
        "Do tada rade evaluate_safety.py, evaluate_nlu.py i evaluate_performance.py.\n"
    )
