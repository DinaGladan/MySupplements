from enum import Enum
from typing import List

from pydantic import BaseModel, Field, field_validator

from app.schemas.profile_schema import ParsedProfile


class GoalType(str, Enum):
    better_sleep = "better_sleep"
    stress_reduction = "stress_reduction"
    mood_support = "mood_support"
    more_energy = "more_energy"
    better_focus = "better_focus"
    recovery = "recovery"
    immune_support = "immune_support"
    physical_performance = "physical_performance"
    heart_health = "heart_health"
    bone_health = "bone_health"
    hair_health = "hair_health"
    skin_health = "skin_health"
    nail_strength = "nail_strength"
    general_health = "general_health"


class ParsedGoals(BaseModel):
    goals: List[GoalType] = Field(default_factory=list)

    @field_validator("goals")
    @classmethod
    def no_duplicates(cls, value: List[GoalType]) -> List[GoalType]:
        return list(dict.fromkeys(value))
