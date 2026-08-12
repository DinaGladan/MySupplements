"""
Parser robustness against negation, missing diacritics, typos and mixed language.

These tests call a running Ollama instance and are therefore excluded from the
default run. Execute them with:

    pytest -m llm

They assert the safe direction only. A parser that returns null for an unclear
statement is acceptable; one that returns the opposite of what the user wrote is
not, because that value goes on to change the recommendation.
"""

import pytest

from app.services.profile_parser_service import parse_profile

pytestmark = pytest.mark.llm


def value_of(field):
    return field.value if hasattr(field, "value") else field


@pytest.mark.parametrize(
    "text",
    [
        "Ne pijem kavu.",
        "I do not drink coffee.",
        "Ne pijem kavu, nikada.",
    ],
)
def test_negated_caffeine_is_never_read_as_high(text):
    assert value_of(parse_profile(text).caffeine_intake) != "high"


@pytest.mark.parametrize(
    "text",
    [
        "Nemam problema sa snom.",
        "I sleep well, no problems at all.",
    ],
)
def test_negated_sleep_problem_is_never_read_as_poor(text):
    assert value_of(parse_profile(text).sleep_quality) != "poor"


@pytest.mark.parametrize(
    "text",
    [
        "Nisam trudna.",
        "I am not pregnant.",
    ],
)
def test_negated_pregnancy_is_never_read_as_true(text):
    assert parse_profile(text).pregnancy is not True


def test_no_stated_allergy_is_never_invented():
    profile = parse_profile("Volim ribu i jedem je često.")
    assert not profile.allergies


def test_dietary_preference_is_not_reported_as_an_allergy():
    profile = parse_profile("Vegetarijanka sam, ne jedem meso.")
    assert not profile.allergies
    assert value_of(profile.diet_type) == "vegetarian"


def test_croatian_without_diacritics_is_still_understood():
    profile = parse_profile("Cesto sam pod stresom i lose spavam.")
    assert value_of(profile.stress_level) in ("medium", "high")
    assert value_of(profile.sleep_quality) == "poor"


def test_common_typos_do_not_break_extraction():
    profile = parse_profile("Imam 27 godina i tesko se koncentiram na poslu.")
    assert profile.age == 27
    assert profile.focus_issues is True


def test_mixed_croatian_and_english_is_understood():
    profile = parse_profile("Imam 25 godina, I am vegan, često sam pod stresom.")
    assert profile.age == 25
    assert value_of(profile.diet_type) == "vegan"
    assert value_of(profile.stress_level) in ("medium", "high")
