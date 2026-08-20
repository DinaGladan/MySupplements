"""
Provjere na razini skupa: uklanjanje redundancije i upozorenja o interakcijama.
"""

import pytest

from app.db.seed import SUPPLEMENTS_DATA
from app.schemas.recommendation_schema import RecommendationItem, ScoreBreakdown
from app.services.safety_service import (
    INTERACTIONS,
    annotate_interactions,
    deduplicate_groups,
    interaction_warnings,
)

GROUPS = {item["name"]: item["nutrient_group"] for item in SUPPLEMENTS_DATA}


def item(name, score=5):
    return RecommendationItem(
        supplement_name=name,
        score_breakdown=ScoreBreakdown(goal_match=score),
        total_score=score,
        reasons=[],
        warnings=[],
    )


def test_every_supplement_has_a_group():
    missing = [i["name"] for i in SUPPLEMENTS_DATA if not i.get("nutrient_group")]
    assert missing == []


def test_best_scoring_member_of_a_group_is_the_one_kept():
    items = [item("b_complex", 8), item("vitamin_b12", 6), item("omega_3", 4)]

    kept, removed = deduplicate_groups(items, GROUPS)

    assert [i.supplement_name for i in kept] == ["b_complex", "omega_3"]
    assert removed == ["vitamin_b12"]


def test_supplements_from_different_groups_are_all_kept():
    items = [item("omega_3"), item("zinc"), item("probiotics")]

    kept, removed = deduplicate_groups(items, GROUPS)

    assert len(kept) == 3
    assert removed == []


def test_supplement_without_a_group_is_never_removed():
    items = [item("first"), item("second")]

    kept, removed = deduplicate_groups(items, {})

    assert len(kept) == 2
    assert removed == []


def test_deduplication_preserves_input_order():
    items = [item("l_theanine", 9), item("omega_3", 7), item("gaba", 5)]

    kept, _ = deduplicate_groups(items, GROUPS)

    assert [i.supplement_name for i in kept] == ["l_theanine", "omega_3"]


def test_interaction_is_reported_only_when_both_members_are_present():
    assert interaction_warnings(["calcium", "iron"])
    assert not interaction_warnings(["calcium"])
    assert not interaction_warnings(["calcium", "omega_3"])


def test_interaction_warning_is_attached_to_both_supplements():
    items = [item("calcium"), item("iron"), item("omega_3")]

    found = annotate_interactions(items)

    assert found == 1
    by_name = {i.supplement_name: i for i in items}
    assert by_name["calcium"].warnings == by_name["iron"].warnings
    assert "apsorpciju željeza" in by_name["calcium"].warnings[0]
    assert by_name["omega_3"].warnings == []


def test_interactions_are_not_added_twice():
    items = [item("calcium"), item("iron")]

    annotate_interactions(items)
    annotate_interactions(items)

    assert len(items[0].warnings) == 1


@pytest.mark.parametrize("pair", list(INTERACTIONS))
def test_interaction_pairs_reference_real_supplements(pair):
    assert pair <= set(GROUPS), f"{pair} nije u bazi znanja"


def test_interaction_never_removes_a_supplement():
    """
    Za razliku od kontraindikacije, nijedan član para nije neprikladan sam po
    sebi — problem je samo u istodobnom uzimanju, pa se oba zadržavaju.
    """
    items = [item("calcium"), item("iron")]

    annotate_interactions(items)

    assert len(items) == 2
