"""Hard contraindications must act as a veto, not as a subtraction.

A soft penalty competes numerically with the positive categories, so enough
goal and profile matches can outvote it and a contraindicated supplement can
still be recommended. These tests pin down that a rule marked "hard": true is
removed from the candidate set instead, and that the old soft behaviour is
still reachable so the two policies can be compared.
"""
import pytest

from app.schemas.goals_schema import GoalType, ParsedGoals
from app.schemas.profile_schema import ActivityLevel, DietType, ParsedProfile
from app.services.scoring_config import ScoringConfig
from app.services.scoring_service import (
    _profile_tokens,
    contraindications,
    score_supplement,
)

VEGAN_WARNING = "Kolagen nije kompatibilan s veganskom prehranom."


@pytest.fixture
def collagen_hard(make_supplement):
    """Animal-derived supplement with a hard contraindication for vegans."""
    return make_supplement(
        "collagen",
        goal_tags=["skin_health", "hair_health", "nail_strength", "recovery"],
        lifestyle={"activity_level:high": 1},
        penalties={
            "diet_type:vegan": {
                "penalty": 4,
                "hard": True,
                "warning": VEGAN_WARNING,
            }
        },
    )


@pytest.fixture
def vegan_profile():
    return ParsedProfile(diet_type=DietType.vegan, activity_level=ActivityLevel.high)


@pytest.fixture
def matching_goals():
    """Four goals that all hit collagen: 4 x 2 = 8 points before the penalty."""
    return ParsedGoals(
        goals=[
            GoalType.skin_health,
            GoalType.hair_health,
            GoalType.nail_strength,
            GoalType.recovery,
        ]
    )


def test_soft_mode_lets_a_contraindicated_supplement_through(
    collagen_hard, vegan_profile, matching_goals
):
    """The problem being fixed: positive matches outvote the penalty."""
    item = score_supplement(
        collagen_hard, vegan_profile, matching_goals, ScoringConfig(safety_mode="soft")
    )

    assert item is not None, "soft mode is expected to still recommend it"
    assert item.total_score >= 5
    assert VEGAN_WARNING in item.warnings


def test_veto_mode_rejects_a_contraindicated_supplement(
    collagen_hard, vegan_profile, matching_goals
):
    """Same input, veto mode: no score is high enough to survive."""
    item = score_supplement(
        collagen_hard, vegan_profile, matching_goals, ScoringConfig(safety_mode="veto")
    )

    assert item is None


def test_veto_is_the_default(collagen_hard, vegan_profile, matching_goals):
    assert score_supplement(collagen_hard, vegan_profile, matching_goals) is None


def test_veto_does_not_fire_when_the_token_is_absent(collagen_hard, matching_goals):
    """An omnivore triggers no contraindication, so the supplement is scored."""
    omnivore = ParsedProfile(activity_level=ActivityLevel.high)

    item = score_supplement(collagen_hard, omnivore, matching_goals)

    assert item is not None
    assert item.warnings == []


def test_soft_penalties_are_untouched_by_veto_mode(make_supplement, matching_goals):
    """A penalty without "hard" stays a score reduction, as before."""
    creatine = make_supplement(
        "creatine",
        goal_tags=["recovery"],
        penalties={
            "activity_level:low": {"penalty": 2, "warning": "Malo koristi bez treninga."}
        },
    )
    sedentary = ParsedProfile(activity_level=ActivityLevel.low)
    goals = ParsedGoals(goals=[GoalType.recovery])

    item = score_supplement(creatine, sedentary, goals, ScoringConfig(min_display_score=0))

    assert item is not None
    assert item.score_breakdown.penalty_risk == 2
    assert item.warnings


def test_contraindications_helper_reports_the_warning(collagen_hard, vegan_profile):
    tokens = _profile_tokens(vegan_profile)

    assert contraindications(collagen_hard, tokens) == [VEGAN_WARNING]


def test_contraindications_helper_ignores_soft_rules(make_supplement):
    supplement = make_supplement(
        "creatine",
        penalties={"activity_level:low": {"penalty": 2, "warning": "meko"}},
    )
    tokens = _profile_tokens(ParsedProfile(activity_level=ActivityLevel.low))

    assert contraindications(supplement, tokens) == []
