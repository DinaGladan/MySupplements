from typing import Any
from app.schemas.goals_schema import GoalType, ParsedGoals
from app.schemas.profile_schema import ParsedProfile


def validate_profile_data(data: dict[str, Any]) -> ParsedProfile:
    """
    Validate raw profile data returned by the LLM.

    Pydantic handles:
    - allowed enum values
    - age constraints
    - boolean validation
    - missing fields
    """

    if not isinstance(data, dict):
        raise ValueError("Profile data must be a dictionary.")

    return ParsedProfile(**data)


def validate_goals_data(data: dict[str, Any]) -> ParsedGoals:
    """
    Validate and clean raw goals data returned by the LLM.

    This function:
    - ensures that goals is a list
    - removes values that are not allowed goals
    - removes duplicate goals
    - returns a valid ParsedGoals object
    """

    if not isinstance(data, dict):
        raise ValueError("Goals data must be a dictionary.")

    raw_goals = data.get("goals", [])

    if not isinstance(raw_goals, list):
        raw_goals = []

    allowed_goals = {goal.value for goal in GoalType}

    cleaned_goals: list[str] = []

    for goal in raw_goals:
        # A weak LLM sometimes emits a goal as an object instead of a string;
        # skip anything that is not a plain string (avoids a TypeError and keeps
        # the other, valid goals).
        if not isinstance(goal, str):
            continue
        if goal in allowed_goals and goal not in cleaned_goals:
            cleaned_goals.append(goal)

    return ParsedGoals(goals=cleaned_goals)
