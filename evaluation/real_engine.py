"""
real_engine.py — spaja stvarni mehanizam iz `app/` na evaluacijske skripte.

`engine_adapter.py` sadrži referentnu implementaciju poglavlja 7. Ovaj modul
umjesto nje poziva `app.services.scoring_service.score_supplement`, dakle isti
kod koji poslužuje `/recommend`. Time se vrednuje stvarni sustav, a ne njegova
replika.

Sučelje je isto kao kod referentnog rangera:
    rank_real(supplements, profile, goals, cfg) -> List[str]

`supplements` su rječnici iz JSON izvoza baze, `profile` je rječnik, `goals`
lista naziva ciljeva, a `cfg` je `ScoringConfig` iz `engine_adapter`. Sve se
pretvara u tipove koje očekuje aplikacija.
"""

from __future__ import annotations

import os
import sys
from typing import List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.schemas.goals_schema import GoalType, ParsedGoals  # noqa: E402
from app.schemas.profile_schema import ParsedProfile  # noqa: E402
from app.services.scoring_config import ScoringConfig as AppScoringConfig  # noqa: E402
from app.services.scoring_service import score_supplement  # noqa: E402

VERY_NEGATIVE = -10**6

SUPPLEMENT_FIELDS = (
    "name",
    "description",
    "goal_tags",
    "state_scores",
    "lifestyle_scores",
    "diet_scores",
    "deficiency_scores",
    "penalties",
)


class _Supplement:
    """Rječnik iz JSON-a predstavljen kao objekt, kakav score_supplement očekuje."""

    def __init__(self, data: dict):
        for field in SUPPLEMENT_FIELDS:
            setattr(self, field, data.get(field))


def to_profile(profile: dict) -> ParsedProfile:
    """
    Nepoznata polja se preskaču, a nedopuštene vrijednosti se odbacuju umjesto da
    sruše cijeli scenarij. Evaluacijski skup piše čovjek i tipfeler u jednom
    polju ne smije obezvrijediti ostatak scenarija.
    """
    allowed = set(ParsedProfile.model_fields)
    clean = {k: v for k, v in (profile or {}).items() if k in allowed and v is not None}

    try:
        return ParsedProfile(**clean)
    except Exception:
        pass

    valid = {}
    for key, value in clean.items():
        try:
            ParsedProfile(**{key: value})
        except Exception:
            continue
        valid[key] = value

    return ParsedProfile(**valid)


def to_goals(goals) -> ParsedGoals:
    allowed = {goal.value for goal in GoalType}
    return ParsedGoals(goals=[g for g in (goals or []) if g in allowed])


def to_app_config(cfg, respect_threshold: bool) -> AppScoringConfig:
    """
    Preslikava ScoringConfig iz engine_adaptera na onaj iz aplikacije.

    Kad se rangira cijela baza (respect_threshold=False) prag prikaza mora
    otpasti, jer bi inače odrezao rep poretka i metrike rangiranja ne bi imale
    što mjeriti.
    """
    app_cfg = AppScoringConfig()

    app_cfg.goal_weight = getattr(cfg, "goal_weight", 2)
    app_cfg.penalty_scale = getattr(cfg, "penalty_scale", 1.0)
    app_cfg.category_scale = dict(getattr(cfg, "category_scale", None) or app_cfg.category_scale)
    app_cfg.enabled = dict(getattr(cfg, "enabled", None) or app_cfg.enabled)
    app_cfg.safety_mode = "veto" if getattr(cfg, "hard_veto", False) else "soft"
    app_cfg.max_recommendations = getattr(cfg, "top_k", 5) or 5
    app_cfg.min_display_score = (
        getattr(cfg, "min_display_score", 4) if respect_threshold else VERY_NEGATIVE
    )

    return app_cfg


def rank_real(supplements, profile, goals, cfg, respect_threshold: bool = False) -> List[str]:
    """
    Rangira dodatke stvarnim mehanizmom aplikacije.

    Poredak je (-ukupno, ime), isto kao u recommendation_engine, kako bi
    izjednačeni rezultati bili deterministički.
    """
    app_cfg = to_app_config(cfg, respect_threshold)
    parsed_profile = to_profile(profile)
    parsed_goals = to_goals(goals)

    scored = []
    for data in supplements:
        item = score_supplement(_Supplement(data), parsed_profile, parsed_goals, app_cfg)
        if item is not None:
            scored.append(item)

    scored.sort(key=lambda item: (-item.total_score, item.supplement_name))

    top_k = app_cfg.max_recommendations if respect_threshold else None
    names = [item.supplement_name for item in scored]

    return names[:top_k] if top_k else names
