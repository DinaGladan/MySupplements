"""Unit tests for the input-language detector."""
from app.utils.language import detect_language


def test_english_input_is_detected_as_english():
    profile = (
        "I am 23 years old, vegetarian female, I sleep ok, I am often stressed, "
        "I feel tired during the day, I drink a lot of coffee."
    )
    goals = "I want to sleep better, have more energy and reduce stress."
    assert detect_language(profile, goals) == "en"


def test_croatian_with_diacritics_is_detected_as_croatian():
    profile = (
        "Imam 23 godine, vegetarijanka sam, loše spavam, često sam pod stresom, "
        "osjećam se umorno i pijem puno kave."
    )
    goals = "Želim bolji san, više energije i smanjiti stres."
    assert detect_language(profile, goals) == "hr"


def test_croatian_without_diacritics_is_detected_as_croatian():
    profile = "Imam 23 godine, cesto sam pod stresom, umoran sam, pijem puno kave."
    goals = "zelim bolji san i vise energije"
    assert detect_language(profile, goals) == "hr"


def test_empty_input_defaults_to_english():
    assert detect_language("", "") == "en"
