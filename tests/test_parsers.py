"""Unit tests for the parser services, including the graceful fallback when the
LLM fails (returns an empty ParsedProfile / ParsedGoals instead of crashing)."""
from app.schemas.goals_schema import GoalType, ParsedGoals
from app.schemas.profile_schema import ParsedProfile, SleepQuality
from app.services import goal_parser_service, profile_parser_service


def test_parse_profile_success(monkeypatch):
    monkeypatch.setattr(
        profile_parser_service.llm_client,
        "complete_json",
        lambda *a, **k: {"age": 30, "sleep_quality": "poor"},
    )
    profile = profile_parser_service.parse_profile("some text")
    assert profile.age == 30
    assert profile.sleep_quality == SleepQuality.poor


def test_parse_profile_falls_back_to_empty_on_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("ollama unavailable")

    monkeypatch.setattr(profile_parser_service.llm_client, "complete_json", boom)
    assert profile_parser_service.parse_profile("some text") == ParsedProfile()


def test_parse_goals_success(monkeypatch):
    monkeypatch.setattr(
        goal_parser_service.llm_client,
        "complete_json",
        lambda *a, **k: {"goals": ["better_sleep", "more_energy"]},
    )
    goals = goal_parser_service.parse_goals("some text")
    assert goals.goals == [GoalType.better_sleep, GoalType.more_energy]


def test_parse_goals_falls_back_to_empty_on_error(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("ollama unavailable")

    monkeypatch.setattr(goal_parser_service.llm_client, "complete_json", boom)
    assert goal_parser_service.parse_goals("some text") == ParsedGoals(goals=[])
