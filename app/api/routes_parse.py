import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.goals_schema import ParsedGoals
from app.schemas.parse_schema import ParsedInputResponse
from app.schemas.profile_schema import ParsedProfile, RawUserInputRequest
from app.services.goal_parser_service import parse_goals
from app.services.profile_parser_service import parse_profile

logger = logging.getLogger(__name__)

router = APIRouter()


class SingleTextRequest(BaseModel):
    text: str


@router.post(
    "/profile",
    response_model=ParsedProfile,
    summary="Parse profile from free text",
    description=(
        "Send a free-text description of a user's lifestyle, habits and health state. "
        "The LLM extracts structured fields (age, sleep quality, stress level, etc.). "
        "Unknown fields are returned as null."
    ),
)
def parse_profile_endpoint(request: SingleTextRequest) -> ParsedProfile:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Profile text must not be empty.")
    try:
        return parse_profile(request.text)
    except Exception as e:
        logger.error(f"Profile parsing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse profile.")


@router.post(
    "/goals",
    response_model=ParsedGoals,
    summary="Parse goals from free text",
    description=(
        "Send a free-text description of what the user wants to achieve. "
        "The LLM maps it to a predefined set of goal labels "
        "(e.g. better_sleep, stress_reduction, more_energy). "
        "Returns an empty list if no clear goal is found."
    ),
)
def parse_goals_endpoint(request: SingleTextRequest) -> ParsedGoals:
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Goals text must not be empty.")
    try:
        return parse_goals(request.text)
    except Exception as e:
        logger.error(f"Goals parsing error: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse goals.")


@router.post(
    "/full",
    response_model=ParsedInputResponse,
    summary="Parse profile and goals in one request",
    description=(
        "Combines /parse/profile and /parse/goals into a single call. "
        "Useful for the main flow where the user submits both texts at once."
    ),
)
def parse_full_endpoint(request: RawUserInputRequest) -> ParsedInputResponse:
    profile = parse_profile(request.profile_text)
    goals = parse_goals(request.goals_text)
    return ParsedInputResponse(profile=profile, goals=goals)
