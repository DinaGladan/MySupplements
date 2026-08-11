"""Unit tests for the LLM-output cleaning layer (validation_service)."""
import pytest

from app.schemas.goals_schema import GoalType
from app.schemas.profile_schema import ParsedProfile, SleepQuality
from app.services.validation_service import validate_goals_data, validate_profile_data


def test_validate_goals_filters_unknown_and_dedupes():
    data = {"goals": ["better_sleep", "better_sleep", "not_a_real_goal", "more_energy"]}
    result = validate_goals_data(data)
    assert result.goals == [GoalType.better_sleep, GoalType.more_energy]


def test_validate_goals_non_list_becomes_empty():
    assert validate_goals_data({"goals": "better_sleep"}).goals == []


def test_validate_goals_skips_non_string_elements():
    # A weak LLM may emit a goal as an object; it must be skipped, not crash,
    # and the valid goals around it must still be kept.
    data = {"goals": ["better_sleep", {"goal": "x"}, "more_energy"]}
    result = validate_goals_data(data)
    assert result.goals == [GoalType.better_sleep, GoalType.more_energy]


def test_validate_goals_missing_key_becomes_empty():
    assert validate_goals_data({}).goals == []


def test_validate_profile_builds_model():
    profile = validate_profile_data({"age": 23, "sleep_quality": "poor"})
    assert isinstance(profile, ParsedProfile)
    assert profile.age == 23
    assert profile.sleep_quality == SleepQuality.poor


def test_validate_profile_rejects_non_dict():
    with pytest.raises(ValueError):
        validate_profile_data("not a dict")
