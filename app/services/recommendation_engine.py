import logging

from sqlalchemy.orm import Session

from app.repositories.supplement_repository import get_all_supplements
from app.schemas.goals_schema import ParsedGoals
from app.schemas.profile_schema import ParsedProfile
from app.schemas.recommendation_schema import RecommendationResponse
from app.services.scoring_service import score_supplement

logger = logging.getLogger(__name__)

# Maximum number of recommendations returned to the user.
MAX_RECOMMENDATIONS = 5


def generate_recommendations(
    db: Session,
    profile: ParsedProfile,
    goals: ParsedGoals,
) -> RecommendationResponse:
    """
    Coordinate the rule-based recommendation flow:
      1. fetch every supplement from the database
      2. score each one against the profile + goals (score_supplement)
      3. drop supplements below the display threshold (score_supplement -> None)
      4. sort by total_score descending
      5. keep only the top MAX_RECOMMENDATIONS

    The LLM is not used here; this is deterministic, rule-based logic.
    """
    supplements = get_all_supplements(db)

    scored = []
    for supplement in supplements:
        item = score_supplement(supplement, profile, goals)
        if item is not None:
            scored.append(item)

    # Highest score first. total_score is already computed by score_supplement.
    scored.sort(key=lambda item: item.total_score, reverse=True)

    top = scored[:MAX_RECOMMENDATIONS]

    logger.info(
        "Generated %d recommendations (from %d supplements).",
        len(top),
        len(supplements),
    )

    return RecommendationResponse(
        recommendations=top,
        profile=profile,
        goals=goals,
    )
