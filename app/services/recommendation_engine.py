import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.supplement_repository import get_all_supplements
from app.schemas.goals_schema import ParsedGoals
from app.schemas.profile_schema import ParsedProfile
from app.schemas.recommendation_schema import RecommendationResponse
from app.services.safety_service import annotate_interactions, deduplicate_groups
from app.services.scoring_config import DEFAULT_CONFIG, ScoringConfig
from app.services.scoring_service import (
    _profile_tokens,
    contraindications,
    score_supplement,
)

logger = logging.getLogger(__name__)

# Maximum number of recommendations returned to the user.
MAX_RECOMMENDATIONS = DEFAULT_CONFIG.max_recommendations


def generate_recommendations(
    db: Session,
    profile: ParsedProfile,
    goals: ParsedGoals,
    cfg: Optional[ScoringConfig] = None,
) -> RecommendationResponse:
    """
    Coordinate the rule-based recommendation flow:
      1. fetch every supplement from the database
      2. reject supplements with a triggered hard contraindication
      3. score the rest against the profile + goals (score_supplement)
      4. drop supplements below the display threshold (score_supplement -> None)
      5. sort by total_score descending
      6. optionally drop supplements redundant with a better-scoring one
      7. keep only the top `cfg.max_recommendations`
      8. attach warnings for known interactions within the final set

    Steps 2-4 all happen inside score_supplement, which returns None in each
    case; the veto count is recomputed here only so it can be logged.

    Steps 6 and 8 look at the set as a whole rather than at single supplements,
    which per-item scoring cannot do.

    The LLM is not used here; this is deterministic, rule-based logic.
    """
    cfg = cfg or DEFAULT_CONFIG
    supplements = get_all_supplements(db)

    scored = []
    for supplement in supplements:
        item = score_supplement(supplement, profile, goals, cfg)
        if item is not None:
            scored.append(item)

    # Highest score first, name as a tie-break. Without the second key the order
    # of equally scored supplements would follow the order the database happened
    # to return them in, so the same profile could produce a different ranking.
    scored.sort(key=lambda item: (-item.total_score, item.supplement_name))

    removed_as_redundant: list[str] = []
    if cfg.resolved_group_dedup():
        groups = {s.name: getattr(s, "nutrient_group", None) for s in supplements}
        scored, removed_as_redundant = deduplicate_groups(scored, groups)

    top = scored[: cfg.max_recommendations]

    interacting_pairs = annotate_interactions(top)

    vetoed = 0
    if cfg.resolved_safety_mode() == "veto":
        tokens = _profile_tokens(profile)
        vetoed = sum(
            1 for s in supplements if contraindications(s, tokens)
        )

    logger.info(
        "Generated %d recommendations (from %d supplements, %d vetoed, "
        "%d dropped as redundant, %d interacting pairs).",
        len(top),
        len(supplements),
        vetoed,
        len(removed_as_redundant),
        interacting_pairs,
    )

    return RecommendationResponse(
        recommendations=top,
        profile=profile,
        goals=goals,
    )
