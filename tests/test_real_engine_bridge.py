"""
The bridge between the evaluation scripts and the real scoring engine.

These tests matter because the bridge is what the numbers in chapter 8 are
produced through. A silent mistake here (a dropped field, a mismapped config)
would not fail anything visibly; it would just quietly report the wrong figures.
"""

import json
import os

import pytest

from evaluation.engine_adapter import ScoringConfig as AdapterConfig
from evaluation.real_engine import rank_real, to_app_config, to_goals, to_profile

SUPPLEMENTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "evaluation",
    "data",
    "supplements.json",
)

TABLE_10_1_PROFILE = {
    "age": 23,
    "gender": "female",
    "sleep_quality": "average",
    "stress_level": "medium",
    "diet_type": "vegetarian",
    "caffeine_intake": "high",
    "sun_exposure": "low",
    "fatigue_level": "medium",
    "focus_issues": True,
}
TABLE_10_1_GOALS = ["better_sleep", "more_energy", "stress_reduction"]


@pytest.fixture
def supplements():
    if not os.path.exists(SUPPLEMENTS_PATH):
        pytest.skip("run evaluation/export_supplements.py first")
    with open(SUPPLEMENTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_unknown_profile_keys_are_ignored():
    profile = to_profile({"age": 30, "favourite_colour": "blue"})
    assert profile.age == 30


def test_invalid_value_drops_only_that_field():
    profile = to_profile({"age": 30, "stress_level": "catastrophic"})
    assert profile.age == 30
    assert profile.stress_level is None


def test_valid_profile_survives_untouched():
    profile = to_profile(TABLE_10_1_PROFILE)
    assert profile.age == 23
    assert profile.diet_type.value == "vegetarian"
    assert profile.focus_issues is True


def test_unknown_goals_are_dropped():
    goals = to_goals(["better_sleep", "become_immortal"])
    assert [goal.value for goal in goals.goals] == ["better_sleep"]


def test_hard_veto_flag_maps_to_safety_mode():
    assert to_app_config(AdapterConfig(hard_veto=True), True).safety_mode == "veto"
    assert to_app_config(AdapterConfig(hard_veto=False), True).safety_mode == "soft"


def test_threshold_is_dropped_when_ranking_the_whole_database():
    """
    Ranking metrics compare full orderings. If the display threshold survived,
    the tail would be cut off and the metrics would measure the wrong thing.
    """
    with_threshold = to_app_config(AdapterConfig(min_display_score=4), True)
    without = to_app_config(AdapterConfig(min_display_score=4), False)

    assert with_threshold.resolved_min_display_score() == 4
    assert without.resolved_min_display_score() < -1000


def test_table_10_1_is_reproduced(supplements):
    ranked = rank_real(
        supplements, TABLE_10_1_PROFILE, TABLE_10_1_GOALS,
        AdapterConfig(), respect_threshold=True,
    )
    assert ranked == [
        "b_complex",
        "l_theanine",
        "ashwagandha",
        "magnesium_glycinate",
        "vitamin_b12",
    ]


def test_ranking_the_whole_database_returns_every_supplement(supplements):
    ranked = rank_real(
        supplements, TABLE_10_1_PROFILE, TABLE_10_1_GOALS,
        AdapterConfig(), respect_threshold=False,
    )
    assert len(ranked) == len(supplements)


def test_veto_removes_a_contraindicated_supplement(supplements):
    profile = {"diet_type": "vegan", "activity_level": "high"}
    goals = ["skin_health", "hair_health", "nail_strength", "recovery"]

    soft = rank_real(supplements, profile, goals, AdapterConfig(hard_veto=False))
    veto = rank_real(supplements, profile, goals, AdapterConfig(hard_veto=True))

    assert "collagen" in soft
    assert "collagen" not in veto


def test_ordering_is_stable_regardless_of_input_order(supplements):
    forwards = rank_real(
        supplements, TABLE_10_1_PROFILE, TABLE_10_1_GOALS, AdapterConfig()
    )
    backwards = rank_real(
        list(reversed(supplements)), TABLE_10_1_PROFILE, TABLE_10_1_GOALS,
        AdapterConfig(),
    )
    assert forwards == backwards
