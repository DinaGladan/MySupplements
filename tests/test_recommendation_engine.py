"""Unit tests for the recommendation engine (DB replaced with in-memory data)."""
from app.schemas.goals_schema import GoalType, ParsedGoals
from app.services import recommendation_engine
from app.services.recommendation_engine import (
    MAX_RECOMMENDATIONS,
    generate_recommendations,
)


def test_recommendations_are_sorted_descending(
    monkeypatch, sample_supplements, profile_sleep_stress, goals_sleep_stress
):
    monkeypatch.setattr(
        recommendation_engine, "get_all_supplements", lambda db: sample_supplements
    )

    result = generate_recommendations(None, profile_sleep_stress, goals_sleep_stress)

    scores = [r.total_score for r in result.recommendations]
    assert scores == sorted(scores, reverse=True)
    assert result.recommendations[0].supplement_name == "magnesium_glycinate"


def test_below_threshold_supplements_are_filtered_out(
    monkeypatch, sample_supplements, profile_sleep_stress, goals_sleep_stress
):
    monkeypatch.setattr(
        recommendation_engine, "get_all_supplements", lambda db: sample_supplements
    )

    result = generate_recommendations(None, profile_sleep_stress, goals_sleep_stress)

    names = {r.supplement_name for r in result.recommendations}
    # These do not reach MIN_DISPLAY_SCORE for this profile/goals.
    assert "b_complex" not in names
    assert "collagen" not in names
    assert "biotin" not in names
    assert all(r.total_score >= 4 for r in result.recommendations)


def test_results_are_capped_at_max(monkeypatch, make_supplement):
    goals = ParsedGoals(
        goals=[GoalType.better_sleep, GoalType.stress_reduction, GoalType.mood_support]
    )
    # 7 supplements that all match all 3 goals -> goal_match 6 each -> all displayed.
    strong = [
        make_supplement(
            f"supp_{i}",
            id=i,
            goal_tags=["better_sleep", "stress_reduction", "mood_support"],
        )
        for i in range(7)
    ]
    monkeypatch.setattr(
        recommendation_engine, "get_all_supplements", lambda db: strong
    )

    from app.schemas.profile_schema import ParsedProfile

    result = generate_recommendations(None, ParsedProfile(), goals)

    assert len(result.recommendations) == MAX_RECOMMENDATIONS == 5
