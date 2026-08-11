"""Unit tests for the deterministic (fallback) explanation builder."""
from app.schemas.goals_schema import GoalType
from app.schemas.recommendation_schema import RecommendationItem, ScoreBreakdown
from app.services.answer_nlg_service import build_explanation


def _item(name, total, reasons=None, warnings=None, matched=None):
    return RecommendationItem(
        supplement_name=name,
        score_breakdown=ScoreBreakdown(goal_match=total),
        total_score=total,
        reasons=reasons or [],
        warnings=warnings or [],
        matched_goals=[GoalType(g) for g in (matched or [])],
    )


def _sample():
    return [
        _item(
            "l_theanine",
            7,
            reasons=[
                "Matches goal: stress_reduction",
                "Matches profile state: stress_level:medium",
                "Matches lifestyle: caffeine_intake:high",
            ],
            matched=["stress_reduction"],
        ),
        _item("b_complex", 7, matched=["more_energy"]),
        _item("magnesium_glycinate", 6, matched=["better_sleep", "stress_reduction"]),
    ]


def test_croatian_explanation_structure():
    text = build_explanation(_sample(), "hr")
    assert "najrelevantniji suplementi su" in text
    assert "Preporučeni suplementi:" in text
    assert "l_theanine" in text
    assert "savjetujte se s liječnikom" in text


def test_english_explanation_structure():
    text = build_explanation(_sample(), "en")
    assert "most relevant supplements are" in text
    assert "Recommended supplements:" in text
    assert "consult a doctor" in text


def test_empty_recommendations_message():
    text = build_explanation([], "en")
    assert "no sufficiently relevant" in text
    assert "consult a doctor" in text


def test_warnings_are_listed():
    recs = [
        _item(
            "collagen",
            5,
            warnings=["Not compatible with a vegan diet."],
            matched=["skin_health"],
        )
    ]
    text = build_explanation(recs, "en")
    assert "Warnings:" in text
    assert "Not compatible with a vegan diet." in text
