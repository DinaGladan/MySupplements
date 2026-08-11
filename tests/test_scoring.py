"""Unit tests for the rule-based scoring service (no DB, no LLM)."""
from app.schemas.goals_schema import GoalType, ParsedGoals
from app.schemas.profile_schema import (
    DietType,
    IntakeLevel,
    ParsedProfile,
    SleepQuality,
    StressLevel,
)
from app.services.scoring_service import score_supplement


def test_goal_match_is_two_points_per_matched_goal(make_supplement):
    supp = make_supplement(
        "magnesium_glycinate",
        goal_tags=["better_sleep", "stress_reduction", "mood_support"],
    )
    profile = ParsedProfile()
    goals = ParsedGoals(goals=[GoalType.better_sleep, GoalType.stress_reduction])

    item = score_supplement(supp, profile, goals)

    assert item is not None
    assert item.score_breakdown.goal_match == 4  # 2 matched goals x 2
    assert item.matched_goals == [GoalType.better_sleep, GoalType.stress_reduction]


def test_state_match_adds_points_and_reasons(make_supplement):
    supp = make_supplement(
        "magnesium_glycinate",
        goal_tags=["better_sleep", "stress_reduction"],
        state={"sleep_quality:poor": 3, "stress_level:high": 3},
    )
    profile = ParsedProfile(
        sleep_quality=SleepQuality.poor, stress_level=StressLevel.high
    )
    goals = ParsedGoals(goals=[GoalType.better_sleep, GoalType.stress_reduction])

    item = score_supplement(supp, profile, goals)

    assert item.score_breakdown.state_match == 6
    assert "Matches profile state: sleep_quality:poor" in item.reasons
    assert "Matches profile state: stress_level:high" in item.reasons


def test_lifestyle_diet_and_deficiency_matches(make_supplement):
    supp = make_supplement(
        "vitamin_d3",
        goal_tags=["immune_support"],
        lifestyle={"caffeine_intake:high": 1},
        diet={"diet_type:vegan": 2},
        deficiency={"sun_exposure:low": 3},
    )
    profile = ParsedProfile(
        caffeine_intake=IntakeLevel.high,
        diet_type=DietType.vegan,
        sun_exposure=IntakeLevel.low,
    )
    goals = ParsedGoals(goals=[GoalType.immune_support])

    item = score_supplement(supp, profile, goals)

    assert item.score_breakdown.lifestyle_match == 1
    assert item.score_breakdown.diet_match == 2
    assert item.score_breakdown.deficiency_risk_proxy == 3


def test_penalty_reduces_score_and_adds_warning(make_supplement):
    supp = make_supplement(
        "collagen",
        goal_tags=["skin_health", "hair_health", "nail_strength"],
        penalties={
            "diet_type:vegan": {"penalty": 2, "warning": "Not vegan-friendly."}
        },
    )
    profile = ParsedProfile(diet_type=DietType.vegan)
    goals = ParsedGoals(
        goals=[GoalType.skin_health, GoalType.hair_health, GoalType.nail_strength]
    )

    item = score_supplement(supp, profile, goals)

    # goal_match 6 - penalty 2 = 4 -> still displayed (>= MIN_DISPLAY_SCORE)
    assert item is not None
    assert item.score_breakdown.penalty_risk == 2
    assert item.total_score == 4
    assert item.warnings == ["Not vegan-friendly."]


def test_supplement_below_threshold_is_dropped(make_supplement):
    supp = make_supplement("melatonin", goal_tags=["better_sleep"])
    profile = ParsedProfile()
    goals = ParsedGoals(goals=[GoalType.better_sleep])

    # Only 1 matched goal -> goal_match 2 -> total 2 < 4 -> None
    assert score_supplement(supp, profile, goals) is None


def test_null_profile_fields_never_match(make_supplement):
    supp = make_supplement(
        "magnesium_glycinate",
        goal_tags=["better_sleep", "stress_reduction", "mood_support"],
        state={"sleep_quality:poor": 3, "stress_level:high": 3},
    )
    profile = ParsedProfile()  # every field is None
    goals = ParsedGoals(
        goals=[GoalType.better_sleep, GoalType.stress_reduction, GoalType.mood_support]
    )

    item = score_supplement(supp, profile, goals)

    assert item.score_breakdown.state_match == 0
    assert item.total_score == 6  # goal_match only


def test_strength_label_reflects_total(make_supplement):
    supp = make_supplement(
        "magnesium_glycinate",
        goal_tags=["better_sleep", "stress_reduction"],
        state={"sleep_quality:poor": 3, "stress_level:high": 3},
        lifestyle={"caffeine_intake:high": 1},
    )
    profile = ParsedProfile(
        sleep_quality=SleepQuality.poor,
        stress_level=StressLevel.high,
        caffeine_intake=IntakeLevel.high,
    )
    goals = ParsedGoals(goals=[GoalType.better_sleep, GoalType.stress_reduction])

    item = score_supplement(supp, profile, goals)

    assert item.total_score == 11
    assert item.strength.value == "very_relevant"
