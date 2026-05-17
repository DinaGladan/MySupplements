from pydantic import BaseModel

from app.schemas.profile_schema import ParsedProfile
from app.schemas.goals_schema import ParsedGoals


class ParsedInputResponse(BaseModel):
    profile: ParsedProfile
    goals: ParsedGoals
