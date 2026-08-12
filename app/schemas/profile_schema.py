from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SleepQuality(str, Enum):
    poor = "poor"
    average = "average"
    good = "good"


class StressLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ActivityLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class DietType(str, Enum):
    omnivore = "omnivore"
    vegetarian = "vegetarian"
    vegan = "vegan"
    pescatarian = "pescatarian"


class IntakeLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class Gender(str, Enum):
    male = "male"
    female = "female"


class Allergy(str, Enum):
    fish = "fish"
    shellfish = "shellfish"
    milk = "milk"
    mushroom = "mushroom"


class RawUserInputRequest(BaseModel):
    profile_text: str = Field(..., min_length=3)
    goals_text: str = Field(..., min_length=3)


class ParsedProfile(BaseModel):
    age: Optional[int] = Field(default=None, gt=0, le=120)
    gender: Optional[Gender] = None
    sleep_quality: Optional[SleepQuality] = None
    stress_level: Optional[StressLevel] = None
    activity_level: Optional[ActivityLevel] = None
    diet_type: Optional[DietType] = None
    fish_intake: Optional[IntakeLevel] = None
    caffeine_intake: Optional[IntakeLevel] = None
    sun_exposure: Optional[IntakeLevel] = None
    fatigue_level: Optional[IntakeLevel] = None
    focus_issues: Optional[bool] = None
    allergies: Optional[list[Allergy]] = None
    pregnancy: Optional[bool] = None
    breastfeeding: Optional[bool] = None
