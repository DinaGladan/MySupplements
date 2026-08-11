"""Endpoint tests via FastAPI TestClient.

Parsers (LLM) and the database are mocked, so these run with no Ollama and no
PostgreSQL. LLM explanation is forced to fail so the deterministic fallback is
used, which lets us assert the explanation language.
"""
from app.api import routes_recommend
from app.api import routes_supplements
from app.config import settings
from app.services import answer_nlg_service, recommendation_engine


def _force_fallback_nlg(monkeypatch):
    """Make the LLM explanation call fail so build_explanation is used."""

    def _boom(*args, **kwargs):
        raise RuntimeError("ollama unavailable")

    monkeypatch.setattr(answer_nlg_service.llm_client, "complete_text", _boom)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_supplements(client, monkeypatch, sample_supplements):
    monkeypatch.setattr(
        routes_supplements, "get_all_supplements", lambda db: sample_supplements
    )

    response = client.get("/supplements")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 5
    assert body[0]["name"] == "magnesium_glycinate"
    # Enriched output includes the scoring data.
    assert "state_scores" in body[0]


def test_recommend_happy_path(
    client, monkeypatch, sample_supplements, profile_sleep_stress, goals_sleep_stress
):
    monkeypatch.setattr(
        routes_recommend, "parse_profile", lambda text: profile_sleep_stress
    )
    monkeypatch.setattr(
        routes_recommend, "parse_goals", lambda text: goals_sleep_stress
    )
    monkeypatch.setattr(
        recommendation_engine, "get_all_supplements", lambda db: sample_supplements
    )
    _force_fallback_nlg(monkeypatch)

    response = client.post(
        "/recommend",
        json={
            "profile_text": "I sleep poorly, I am stressed and drink a lot of coffee.",
            "goals_text": "I want better sleep and less stress.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["recommendations"], "expected at least one recommendation"
    assert body["recommendations"][0]["supplement_name"] == "magnesium_glycinate"
    # English input -> English explanation.
    assert "Recommended supplements:" in body["explanation"]


def test_recommend_croatian_input_gets_croatian_explanation(
    client, monkeypatch, sample_supplements, profile_sleep_stress, goals_sleep_stress
):
    monkeypatch.setattr(
        routes_recommend, "parse_profile", lambda text: profile_sleep_stress
    )
    monkeypatch.setattr(
        routes_recommend, "parse_goals", lambda text: goals_sleep_stress
    )
    monkeypatch.setattr(
        recommendation_engine, "get_all_supplements", lambda db: sample_supplements
    )
    _force_fallback_nlg(monkeypatch)

    response = client.post(
        "/recommend",
        json={
            "profile_text": "Loše spavam, često sam pod stresom i pijem puno kave.",
            "goals_text": "Želim bolji san i manje stresa.",
        },
    )

    assert response.status_code == 200
    assert "Preporučeni suplementi:" in response.json()["explanation"]


def test_recommend_uses_llm_explanation_when_enabled(
    client, monkeypatch, sample_supplements, profile_sleep_stress, goals_sleep_stress
):
    monkeypatch.setattr(
        routes_recommend, "parse_profile", lambda text: profile_sleep_stress
    )
    monkeypatch.setattr(
        routes_recommend, "parse_goals", lambda text: goals_sleep_stress
    )
    monkeypatch.setattr(
        recommendation_engine, "get_all_supplements", lambda db: sample_supplements
    )
    # Turn the LLM explanation ON and stub it with a marker string.
    monkeypatch.setattr(settings, "use_llm_explanation", True)
    monkeypatch.setattr(
        routes_recommend,
        "generate_recommendation_text",
        lambda recs, language: "LLM_EXPLANATION_MARKER",
    )

    response = client.post(
        "/recommend",
        json={"profile_text": "stressed, poor sleep", "goals_text": "sleep better"},
    )

    assert response.status_code == 200
    assert response.json()["explanation"] == "LLM_EXPLANATION_MARKER"


def test_recommend_blank_profile_returns_400(client):
    response = client.post(
        "/recommend",
        json={"profile_text": "   ", "goals_text": "I want better sleep."},
    )
    assert response.status_code == 400
