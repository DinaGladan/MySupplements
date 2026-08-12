import pytest

from app.db.seed import SUPPLEMENTS_DATA
from app.schemas.goals_schema import ParsedGoals
from app.schemas.profile_schema import ParsedProfile
from app.services.scoring_config import ScoringConfig
from app.services.scoring_service import (
    _profile_tokens,
    contraindications,
    score_supplement,
)
from app.services.validation_service import validate_profile_data


class FakeSupplement:
    def __init__(self, data):
        self.__dict__.update(data)


def supplement(name):
    for item in SUPPLEMENTS_DATA:
        if item["name"] == name:
            return FakeSupplement(item)
    raise AssertionError(f"{name} missing from seed data")


def blocked_for(profile):
    tokens = _profile_tokens(profile)
    return {
        item["name"]
        for item in SUPPLEMENTS_DATA
        if contraindications(FakeSupplement(item), tokens)
    }


def test_allergy_tokens_are_generated_per_allergen():
    profile = ParsedProfile(allergies=["fish", "milk"])
    assert _profile_tokens(profile) == {"allergy:fish", "allergy:milk"}


def test_pregnancy_token_is_generated():
    assert "pregnancy:true" in _profile_tokens(ParsedProfile(pregnancy=True))


def test_pregnancy_false_does_not_trigger_pregnancy_rules():
    assert blocked_for(ParsedProfile(pregnancy=False)) == set()


@pytest.mark.parametrize(
    "allergen,expected",
    [
        ("fish", {"omega_3", "collagen"}),
        ("shellfish", {"glucosamine_chondroitin"}),
        ("milk", {"protein_powder"}),
        ("mushroom", {"lions_mane"}),
    ],
)
def test_each_allergen_blocks_its_supplements(allergen, expected):
    assert blocked_for(ParsedProfile(allergies=[allergen])) == expected


def test_pregnancy_blocks_the_documented_set():
    expected = {
        "ashwagandha",
        "valerian_root",
        "rhodiola_rosea",
        "melatonin",
        "gaba",
        "resveratrol",
        "curcumin",
        "lions_mane",
    }
    assert blocked_for(ParsedProfile(pregnancy=True)) == expected


@pytest.mark.parametrize(
    "name", ["iron", "omega_3", "vitamin_d3", "calcium", "b_complex", "vitamin_b12"]
)
def test_pregnancy_keeps_the_supplements_that_stay_allowed(name):
    assert name not in blocked_for(ParsedProfile(pregnancy=True))


def test_breastfeeding_blocks_the_same_set_as_pregnancy():
    assert blocked_for(ParsedProfile(breastfeeding=True)) == blocked_for(
        ParsedProfile(pregnancy=True)
    )


def test_breastfeeding_false_does_not_trigger_breastfeeding_rules():
    assert blocked_for(ParsedProfile(breastfeeding=False)) == set()


def test_fish_allergy_removes_omega_3_from_recommendations():
    """
    The display threshold is lowered so that a None result can only come from the
    veto. Otherwise the supplement would drop out on score alone and the test
    would pass without exercising the safety stage at all.
    """
    profile = ParsedProfile(allergies=["fish"])
    goals = ParsedGoals(goals=["heart_health"])
    cfg = ScoringConfig(min_display_score=-10)
    assert score_supplement(supplement("omega_3"), profile, goals, cfg) is None


def test_soft_mode_keeps_an_allergy_contraindicated_supplement():
    profile = ParsedProfile(allergies=["fish"])
    goals = ParsedGoals(goals=["heart_health"])
    cfg = ScoringConfig(safety_mode="soft", min_display_score=-10)
    result = score_supplement(supplement("omega_3"), profile, goals, cfg)
    assert result is not None
    assert any("alergije na ribu" in warning for warning in result.warnings)


def test_probiotics_milk_rule_is_soft_and_only_warns():
    profile = ParsedProfile(allergies=["milk"])
    goals = ParsedGoals(goals=["immune_support"])
    cfg = ScoringConfig(min_display_score=-10)
    result = score_supplement(supplement("probiotics"), profile, goals, cfg)
    assert result is not None
    assert any("mliječnoj podlozi" in warning for warning in result.warnings)


def test_vegan_vitamin_d3_rule_is_soft_and_only_warns():
    profile = ParsedProfile(diet_type="vegan", sun_exposure="low")
    goals = ParsedGoals(goals=["immune_support"])
    result = score_supplement(supplement("vitamin_d3"), profile, goals)
    assert result is not None
    assert any("lanolina" in warning for warning in result.warnings)


def test_unknown_allergen_is_dropped_without_discarding_the_profile():
    profile = validate_profile_data(
        {"age": 30, "diet_type": "vegan", "allergies": ["peanut", "fish"]}
    )
    assert profile.age == 30
    assert profile.diet_type.value == "vegan"
    assert [allergy.value for allergy in profile.allergies] == ["fish"]


def test_allergies_given_as_a_string_do_not_discard_the_profile():
    profile = validate_profile_data({"age": 30, "allergies": "fish"})
    assert profile.age == 30
    assert profile.allergies is None
