import logging
from typing import Optional

from app.models.supplement import Supplement
from app.schemas.goals_schema import GoalType, ParsedGoals
from app.schemas.profile_schema import ParsedProfile
from app.schemas.recommendation_schema import RecommendationItem, ScoreBreakdown
from app.services.scoring_config import DEFAULT_CONFIG, ScoringConfig

logger = logging.getLogger(__name__)

GOAL_MATCH_WEIGHT = DEFAULT_CONFIG.goal_weight


def _profile_tokens(profile: ParsedProfile) -> set[str]:
    """
    Turn a ParsedProfile into a set of "field:value" tokens that can be looked
    up directly in a supplement's score dictionaries (state_scores,
    lifestyle_scores, diet_scores, deficiency_scores, penalties).

    Only fields that were actually extracted (non-None) produce a token, so a
    field left as null in the profile never matches anything. Example tokens:
    "sleep_quality:poor", "stress_level:high", "diet_type:vegan",
    "focus_issues:true".
    """
    tokens: set[str] = set()

    # Enum / string fields -> "field:value"
    simple_fields = {
        "gender": profile.gender,
        "sleep_quality": profile.sleep_quality,
        "stress_level": profile.stress_level,
        "activity_level": profile.activity_level,
        "diet_type": profile.diet_type,
        "fish_intake": profile.fish_intake,
        "caffeine_intake": profile.caffeine_intake,
        "sun_exposure": profile.sun_exposure,
        "fatigue_level": profile.fatigue_level,
    }

    for field, value in simple_fields.items():
        if value is not None:
            token_value = value.value if hasattr(value, "value") else value
            tokens.add(f"{field}:{token_value}")

    if profile.focus_issues is not None:
        tokens.add(f"focus_issues:{str(profile.focus_issues).lower()}")

    if profile.pregnancy is not None:
        tokens.add(f"pregnancy:{str(profile.pregnancy).lower()}")

    if profile.breastfeeding is not None:
        tokens.add(f"breastfeeding:{str(profile.breastfeeding).lower()}")

    for allergy in profile.allergies or []:
        token_value = allergy.value if hasattr(allergy, "value") else allergy
        tokens.add(f"allergy:{token_value}")

    return tokens


def _score_category(
    score_map: Optional[dict],
    profile_tokens: set[str],
    reasons: list[str],
    reason_label: str,
    cap: Optional[int] = None,
) -> int:
    """
    Sum the points for every "field:value" key in `score_map` that is present
    in the user's profile tokens, appending a human-readable reason per hit.

    `cap` bounds how much a single category may contribute. It exists because
    an additive model rewards supplements that simply carry more scoring
    entries; capping lets the evaluation test whether breadth, rather than fit,
    is driving the ranking. Default (None) leaves the original behaviour.
    """
    subtotal = 0

    for key, points in (score_map or {}).items():
        if key in profile_tokens:
            subtotal += points
            reasons.append(f"{reason_label}: {key}")

    if cap is not None:
        subtotal = min(subtotal, cap)

    return subtotal


def contraindications(
    supplement: Supplement,
    profile_tokens: set[str],
) -> list[str]:
    """
    Return the warnings of every *hard* penalty rule triggered by this profile.

    A penalty rule counts as a contraindication only when it is explicitly
    marked with "hard": true. Rules without that flag stay soft score
    reductions, so existing knowledge-base entries keep their old meaning.
    """
    triggered: list[str] = []

    for key, rule in (supplement.penalties or {}).items():
        if key in profile_tokens and rule.get("hard"):
            triggered.append(rule.get("warning") or key)

    return triggered


def score_supplement(
    supplement: Supplement,
    profile: ParsedProfile,
    goals: ParsedGoals,
    cfg: Optional[ScoringConfig] = None,
) -> Optional[RecommendationItem]:
    """
    Score a single supplement against a parsed profile and parsed goals using
    only the rule/scoring data stored on the supplement itself.

    The decision runs in two stages:

      1. veto      - if a hard contraindication is triggered (and safety_mode
                     is "veto"), the supplement is rejected outright. A
                     contraindication must not compete numerically with
                     benefits: enough positive matches could otherwise outvote
                     it, which is unacceptable in a health-adjacent domain.

      2. scoring   - total_score =
                         goal_match
                         + state_match
                         + lifestyle_match
                         + diet_match
                         + deficiency_risk_proxy
                         - penalty_risk

    Returns a RecommendationItem, or None if the supplement is contraindicated
    or scores below the display threshold.

    `cfg` exists for the evaluation (ablation, sensitivity, soft-vs-veto
    comparison). Passing None uses the production defaults.

    NOTE: this is a purely rule-based function.
    """
    cfg = cfg or DEFAULT_CONFIG

    reasons: list[str] = []
    warnings: list[str] = []

    profile_tokens = _profile_tokens(profile)

    if cfg.resolved_safety_mode() == "veto":
        blocking = contraindications(supplement, profile_tokens)
        if blocking:
            logger.info(
                "Vetoed %s (contraindicated): %s",
                supplement.name,
                "; ".join(blocking),
            )
            return None

    supplement_goal_tags = set(supplement.goal_tags or [])
    matched_goals: list[GoalType] = [
        goal for goal in goals.goals if goal.value in supplement_goal_tags
    ]

    goal_match = 0
    if cfg.enabled.get("goal_match", True):
        goal_match = cfg.goal_weight * len(matched_goals)
        for goal in matched_goals:
            reasons.append(f"Matches goal: {goal.value}")

    def category(name: str, score_map, label: str) -> int:
        if not cfg.enabled.get(name, True):
            return 0
        raw = _score_category(
            score_map, profile_tokens, reasons, label, cap=cfg.category_cap
        )
        return int(round(cfg.category_scale.get(name, 1.0) * raw))

    state_match = category(
        "state_match", supplement.state_scores, "Matches profile state"
    )
    lifestyle_match = category(
        "lifestyle_match", supplement.lifestyle_scores, "Matches lifestyle"
    )
    diet_match = category("diet_match", supplement.diet_scores, "Matches diet")
    deficiency_risk_proxy = category(
        "deficiency_risk_proxy",
        supplement.deficiency_scores,
        "Possible deficiency risk",
    )

    penalty_risk = 0
    for key, rule in (supplement.penalties or {}).items():
        if key in profile_tokens:
            if cfg.enabled.get("penalty", True):
                penalty_risk += rule.get("penalty", 0)
            warning = rule.get("warning")
            if warning:
                warnings.append(warning)

    penalty_risk = int(round(penalty_risk * cfg.penalty_scale))

    breakdown = ScoreBreakdown(
        goal_match=goal_match,
        state_match=state_match,
        lifestyle_match=lifestyle_match,
        diet_match=diet_match,
        deficiency_risk_proxy=deficiency_risk_proxy,
        penalty_risk=penalty_risk,
    )

    total_score = breakdown.total

    if total_score < cfg.resolved_min_display_score():
        return None

    return RecommendationItem(
        supplement_name=supplement.name,
        score_breakdown=breakdown,
        total_score=total_score,
        reasons=reasons,
        warnings=warnings,
        matched_goals=matched_goals,
    )
