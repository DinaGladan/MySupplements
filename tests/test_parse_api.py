"""Endpoint tests for the /parse/* routes (parsers mocked, no Ollama)."""
from app.api import routes_parse
from app.schemas.goals_schema import GoalType, ParsedGoals
from app.schemas.profile_schema import ParsedProfile


def test_parse_profile_endpoint(client, monkeypatch):
    monkeypatch.setattr(routes_parse, "parse_profile", lambda text: ParsedProfile(age=25))
    response = client.post("/parse/profile", json={"text": "I am 25 years old"})
    assert response.status_code == 200
    assert response.json()["age"] == 25


def test_parse_profile_empty_returns_400(client):
    response = client.post("/parse/profile", json={"text": "   "})
    assert response.status_code == 400


def test_parse_goals_endpoint(client, monkeypatch):
    monkeypatch.setattr(
        routes_parse, "parse_goals", lambda text: ParsedGoals(goals=[GoalType.better_sleep])
    )
    response = client.post("/parse/goals", json={"text": "I want to sleep better"})
    assert response.status_code == 200
    assert response.json()["goals"] == ["better_sleep"]


def test_parse_goals_empty_returns_400(client):
    response = client.post("/parse/goals", json={"text": ""})
    assert response.status_code == 400
