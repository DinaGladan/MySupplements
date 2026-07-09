import logging
from typing import Optional

from app.config import settings
from app.models.supplement import Supplement
from app.schemas.goals_schema import GoalType, ParsedGoals
from app.schemas.profile_schema import ParsedProfile
from app.schemas.recommendation_schema import RecommendationItem, ScoreBreakdown

logger = logging.getLogger(__name__)

GOAL_MATCH_WEIGHT = 2


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

    return tokens


def _score_category(
    score_map: Optional[dict],
    profile_tokens: set[str],
    reasons: list[str],
    reason_label: str,
) -> int:
    """
    Sum the points for every "field:value" key in `score_map` that is present
    in the user's profile tokens, appending a human-readable reason per hit.
    """
    subtotal = 0

    for key, points in (score_map or {}).items():
        if key in profile_tokens:
            subtotal += points
            reasons.append(f"{reason_label}: {key}")

    return subtotal


def score_supplement(
    supplement: Supplement,
    profile: ParsedProfile,
    goals: ParsedGoals,
) -> Optional[RecommendationItem]:
    """
    Score a single supplement against a parsed profile and parsed goals using
    only the rule/scoring data stored on the supplement itself.

    total_score =
        goal_match
        + state_match
        + lifestyle_match
        + diet_match
        + deficiency_risk_proxy
        - penalty_risk

    Returns a RecommendationItem, or None if the supplement scores below
    settings.min_display_score (meaning it should not be shown to the user).

    NOTE: this is a purely rule-based function.
    """
    reasons: list[str] = []
    warnings: list[str] = []

    profile_tokens = _profile_tokens(profile)

    # --- goal_match: overlap between user goals and supplement.goal_tags ---
    supplement_goal_tags = set(supplement.goal_tags or [])
    matched_goals: list[GoalType] = [
        goal for goal in goals.goals if goal.value in supplement_goal_tags
    ]

    goal_match = GOAL_MATCH_WEIGHT * len(matched_goals)
    for goal in matched_goals:
        reasons.append(f"Matches goal: {goal.value}")

    state_match = _score_category(
        supplement.state_scores, profile_tokens, reasons, "Matches profile state"
    )
    lifestyle_match = _score_category(
        supplement.lifestyle_scores, profile_tokens, reasons, "Matches lifestyle"
    )
    diet_match = _score_category(
        supplement.diet_scores, profile_tokens, reasons, "Matches diet"
    )
    deficiency_risk_proxy = _score_category(
        supplement.deficiency_scores,
        profile_tokens,
        reasons,
        "Possible deficiency risk",
    )

    penalty_risk = 0
    for key, rule in (supplement.penalties or {}).items():
        if key in profile_tokens:
            penalty_risk += rule.get("penalty", 0)
            warning = rule.get("warning")
            if warning:
                warnings.append(warning)

    breakdown = ScoreBreakdown(
        goal_match=goal_match,
        state_match=state_match,
        lifestyle_match=lifestyle_match,
        diet_match=diet_match,
        deficiency_risk_proxy=deficiency_risk_proxy,
        penalty_risk=penalty_risk,
    )

    total_score = breakdown.total

    if total_score < settings.min_display_score:
        return None

    return RecommendationItem(
        supplement_name=supplement.name,
        score_breakdown=breakdown,
        total_score=total_score,
        reasons=reasons,
        warnings=warnings,
        matched_goals=matched_goals,
    )
