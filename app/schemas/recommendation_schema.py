from enum import Enum
from typing import List

from pydantic import BaseModel, Field, computed_field

from app.schemas.goals_schema import GoalType, ParsedGoals
from app.schemas.profile_schema import ParsedProfile


class RecommendationStrength(str, Enum):
    weak = "weak"
    good = "good"
    very_relevant = "very_relevant"


class ScoreBreakdown(BaseModel):
    goal_match: int = 0
    state_match: int = 0
    lifestyle_match: int = 0
    diet_match: int = 0
    deficiency_risk_proxy: int = 0
    penalty_risk: int = 0

    @computed_field
    @property
    def total(self) -> int:
        return (
            self.goal_match
            + self.state_match
            + self.lifestyle_match
            + self.diet_match
            + self.deficiency_risk_proxy
            - self.penalty_risk
        )


class RecommendationItem(BaseModel):
    supplement_name: str
    score_breakdown: ScoreBreakdown
    total_score: int
    reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    matched_goals: List[GoalType] = Field(default_factory=list)

    @computed_field
    @property
    def strength(self) -> RecommendationStrength:
        if self.total_score >= 7:
            return RecommendationStrength.very_relevant
        if self.total_score >= 5:
            return RecommendationStrength.good
        return RecommendationStrength.weak


class RecommendationResponse(BaseModel):
    recommendations: List[RecommendationItem] = Field(default_factory=list)
    profile: ParsedProfile
    goals: ParsedGoals
