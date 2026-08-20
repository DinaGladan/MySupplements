"""
Tunable parameters for the rule-based scoring engine.

The application always runs with the defaults, which reproduce the behaviour
described in chapter 7 of the thesis. These values are configurable only so the
evaluation can vary exactly one thing at a time: the ablation study switches
individual categories off, the sensitivity analysis perturbs single weights,
and the safety comparison switches between soft penalties and a hard veto.

Fields left as None fall back to app.config.settings at call time, so
overriding a setting in a test still works as before.
"""

from dataclasses import dataclass, field
from typing import Optional

POSITIVE_CATEGORIES = (
    "goal_match",
    "state_match",
    "lifestyle_match",
    "diet_match",
    "deficiency_risk_proxy",
)

CATEGORY_TO_COLUMN = {
    "state_match": "state_scores",
    "lifestyle_match": "lifestyle_scores",
    "diet_match": "diet_scores",
    "deficiency_risk_proxy": "deficiency_scores",
}


def _default_scale() -> dict[str, float]:
    return {category: 1.0 for category in CATEGORY_TO_COLUMN}


def _default_enabled() -> dict[str, bool]:
    return {category: True for category in (*POSITIVE_CATEGORIES, "penalty")}


@dataclass
class ScoringConfig:
    """
    Parameters of the scoring model.

    goal_weight      points awarded per matched user goal
    category_scale   per-category multiplier, varied by the sensitivity analysis
    penalty_scale    multiplier applied to soft penalties
    enabled          ablation switches; False removes that category entirely
    category_cap     upper bound on one category's contribution, None = no cap
    safety_mode      "veto" or "soft"; None falls back to settings
    """

    goal_weight: int = 2
    category_scale: dict[str, float] = field(default_factory=_default_scale)
    penalty_scale: float = 1.0
    enabled: dict[str, bool] = field(default_factory=_default_enabled)
    category_cap: Optional[int] = None
    min_display_score: Optional[int] = None
    safety_mode: Optional[str] = None
    group_dedup: Optional[bool] = None
    max_recommendations: int = 5

    def resolved_min_display_score(self) -> int:
        if self.min_display_score is not None:
            return self.min_display_score
        from app.config import settings

        return settings.min_display_score

    def resolved_safety_mode(self) -> str:
        if self.safety_mode is not None:
            return self.safety_mode
        from app.config import settings

        return settings.safety_mode

    def resolved_group_dedup(self) -> bool:
        if self.group_dedup is not None:
            return self.group_dedup
        from app.config import settings

        return settings.group_dedup

    def replace(self, **overrides) -> "ScoringConfig":
        """Return a copy with some fields overridden (used by the evaluation)."""
        import copy

        clone = copy.deepcopy(self)
        for key, value in overrides.items():
            if not hasattr(clone, key):
                raise AttributeError(f"Unknown ScoringConfig field: {key}")
            setattr(clone, key, value)
        return clone


DEFAULT_CONFIG = ScoringConfig()
