import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.explanation_schema import FinalRecommendationResponse
from app.schemas.profile_schema import RawUserInputRequest
from app.services.answer_nlg_service import (
    build_explanation,
    generate_recommendation_text,
)
from app.services.goal_parser_service import parse_goals
from app.services.profile_parser_service import parse_profile
from app.services.recommendation_engine import generate_recommendations
from app.utils.language import detect_language

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=FinalRecommendationResponse,
    summary="Full recommendation flow from free text",
    description=(
        "The main endpoint. Send free-text profile and goals; the backend "
        "parses both with the LLM, runs the rule-based recommendation engine, "
        "and returns the parsed profile, parsed goals, ranked recommendations "
        "and a natural-language explanation.\n\n"
        "The supplement selection itself is rule-based; the LLM only parses the "
        "input text and writes the final explanation."
    ),
)
def recommend(
    request: RawUserInputRequest,
    db: Session = Depends(get_db),
) -> FinalRecommendationResponse:
    # Extra guard on top of Pydantic's min_length: reject whitespace-only text.
    if not request.profile_text.strip():
        raise HTTPException(status_code=400, detail="profile_text must not be empty.")
    if not request.goals_text.strip():
        raise HTTPException(status_code=400, detail="goals_text must not be empty.")

    # 1 + 2: parse profile and goals.
    # The parser services already fall back to an empty ParsedProfile / ParsedGoals
    # if Ollama is down or returns invalid JSON, so parsing never raises here.
    profile = parse_profile(request.profile_text)
    goals = parse_goals(request.goals_text)

    # 3-7: rule-based scoring, filtering and ranking.
    try:
        result = generate_recommendations(db, profile, goals)
    except SQLAlchemyError as e:
        logger.error(f"Database error during recommendation: {e}")
        raise HTTPException(
            status_code=503, detail="Database is currently unavailable."
        )

    # 8: natural-language explanation, in the same language as the user's input.
    # generate_recommendation_text has its own fallback if Ollama is unavailable.
    language = detect_language(request.profile_text, request.goals_text)

    if result.recommendations:
        explanation = generate_recommendation_text(result.recommendations, language)
    else:
        # No LLM call when there is nothing to explain.
        explanation = build_explanation(result.recommendations, language)

    # 9: final response.
    return FinalRecommendationResponse(
        profile=profile,
        goals=goals,
        recommendations=result.recommendations,
        explanation=explanation,
    )
