"""
Absent field vs explicitly false.

A field left as null means the user said nothing about it, while false means the
user denied it. The two must not collapse into each other: a rule keyed on
"focus_issues:false" should fire only for a user who actually denied the problem,
and never for one who simply did not mention it.
"""

from app.schemas.goals_schema import ParsedGoals
from app.schemas.profile_schema import ParsedProfile
from app.services.scoring_config import ScoringConfig
from app.services.scoring_service import _profile_tokens, score_supplement


class FakeSupplement:
    def __init__(self, **data):
        self.name = "test_supplement"
        self.goal_tags = []
        self.state_scores = {}
        self.lifestyle_scores = {}
        self.diet_scores = {}
        self.deficiency_scores = {}
        self.penalties = {}
        self.__dict__.update(data)


def test_absent_boolean_produces_no_token():
    tokens = _profile_tokens(ParsedProfile())
    assert not any(token.startswith("focus_issues:") for token in tokens)
    assert not any(token.startswith("pregnancy:") for token in tokens)
    assert not any(token.startswith("breastfeeding:") for token in tokens)


def test_false_boolean_produces_a_false_token():
    tokens = _profile_tokens(ParsedProfile(focus_issues=False, pregnancy=False))
    assert "focus_issues:false" in tokens
    assert "pregnancy:false" in tokens
    assert "focus_issues:true" not in tokens
    assert "pregnancy:true" not in tokens


def test_absent_list_and_empty_list_both_produce_no_tokens():
    for value in (None, []):
        tokens = _profile_tokens(ParsedProfile(allergies=value))
        assert not any(token.startswith("allergy:") for token in tokens)


def test_rule_on_false_does_not_fire_for_an_absent_field():
    supplement = FakeSupplement(state_scores={"focus_issues:false": 3})
    goals = ParsedGoals(goals=[])
    cfg = ScoringConfig(min_display_score=-10)

    absent = score_supplement(supplement, ParsedProfile(), goals, cfg)
    denied = score_supplement(
        supplement, ParsedProfile(focus_issues=False), goals, cfg
    )

    assert absent.score_breakdown.state_match == 0
    assert denied.score_breakdown.state_match == 3


def test_rule_on_true_does_not_fire_for_an_explicit_false():
    supplement = FakeSupplement(state_scores={"focus_issues:true": 3})
    goals = ParsedGoals(goals=[])
    cfg = ScoringConfig(min_display_score=-10)

    result = score_supplement(
        supplement, ParsedProfile(focus_issues=False), goals, cfg
    )

    assert result.score_breakdown.state_match == 0


def test_denying_pregnancy_does_not_trigger_the_pregnancy_veto():
    supplement = FakeSupplement(
        penalties={
            "pregnancy:true": {"penalty": 4, "hard": True, "warning": "test"}
        }
    )
    goals = ParsedGoals(goals=[])
    cfg = ScoringConfig(min_display_score=-10)

    assert score_supplement(supplement, ParsedProfile(pregnancy=False), goals, cfg)
    assert score_supplement(supplement, ParsedProfile(), goals, cfg)
    assert score_supplement(supplement, ParsedProfile(pregnancy=True), goals, cfg) is None


def test_pregnancy_and_breastfeeding_are_independent_states():
    tokens = _profile_tokens(ParsedProfile(pregnancy=False, breastfeeding=True))
    assert "breastfeeding:true" in tokens
    assert "pregnancy:true" not in tokens
