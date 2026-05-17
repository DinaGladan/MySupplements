from typing import List

from pydantic import BaseModel, Field

from app.schemas.goals_schema import ParsedGoals
from app.schemas.profile_schema import ParsedProfile
from app.schemas.recommendation_schema import RecommendationItem


class ExplanationRequest(BaseModel):
    recommendations: List[RecommendationItem]
    profile: ParsedProfile
    goals: ParsedGoals


class ExplanationResponse(BaseModel):
    explanation: str
    recommendations: List[RecommendationItem] = Field(default_factory=list)


class FinalRecommendationResponse(BaseModel):
    profile: ParsedProfile
    goals: ParsedGoals
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    explanation: str
