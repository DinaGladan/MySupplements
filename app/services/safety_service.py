"""
Provjere na razini cijelog skupa preporuka.

Bodovanje ocjenjuje svaki dodatak zasebno, pa prvih pet može biti loše kao skup
iako je svaki član pojedinačno dobar. Dvije su takve situacije:

  redundancija   - dva dodatka iz iste skupine hranjivih tvari, npr. b_complex i
                   vitamin_b12, gdje drugi ne donosi ništa preko prvog

  interakcija    - dva dodatka koja se međusobno ometaju, npr. kalcij i željezo,
                   koji se natječu za istu apsorpcijsku putanju

Redundancija se uklanja samo kad je `group_dedup` uključen. Zadano je isključena
jer mjerenje pokazuje da označivači preklapajuće dodatke smatraju relevantnima;
usporedba obaju načina je sama po sebi rezultat.

Interakcije se nikada ne uklanjaju nego samo prijavljuju. Za razliku od
kontraindikacije, ovdje nijedan dodatak nije neprikladan sam po sebi — problem je
u tome što se uzimaju zajedno, a to korisnik može riješiti razmakom između doza.
"""

import logging
from typing import Iterable, Optional

from app.schemas.recommendation_schema import RecommendationItem

logger = logging.getLogger(__name__)

INTERACTIONS: dict[frozenset[str], str] = {
    frozenset({"calcium", "iron"}): (
        "Kalcij smanjuje apsorpciju željeza. Uzimajte ih s najmanje dva sata razmaka."
    ),
    frozenset({"zinc", "iron"}): (
        "Cink i željezo natječu se za istu apsorpcijsku putanju. Nemojte ih uzimati istodobno."
    ),
    frozenset({"calcium", "zinc"}): (
        "Kalcij u većim dozama smanjuje apsorpciju cinka. Razdvojite ih tijekom dana."
    ),
}


def deduplicate_groups(
    items: list[RecommendationItem],
    groups: dict[str, Optional[str]],
) -> tuple[list[RecommendationItem], list[str]]:
    """
    Zadrži najbolje ocijenjeni dodatak iz svake skupine hranjivih tvari.

    Ulazna lista mora već biti sortirana, jer se zadržava prvi viđeni član
    skupine. Dodatak bez skupine tretira se kao vlastita skupina i nikada se ne
    uklanja.

    Vraća pročišćenu listu i nazive uklonjenih dodataka.
    """
    kept: list[RecommendationItem] = []
    removed: list[str] = []
    seen: set[str] = set()

    for item in items:
        group = groups.get(item.supplement_name) or item.supplement_name
        if group in seen:
            removed.append(item.supplement_name)
            continue
        seen.add(group)
        kept.append(item)

    return kept, removed


def interaction_warnings(names: Iterable[str]) -> list[tuple[frozenset[str], str]]:
    """Poznati parovi koji su se našli u istom skupu, s pripadnim upozorenjem."""
    present = set(names)
    return [
        (pair, warning)
        for pair, warning in INTERACTIONS.items()
        if pair <= present
    ]


def annotate_interactions(items: list[RecommendationItem]) -> int:
    """
    Dodaj upozorenje o interakciji objema stavkama para.

    Upozorenje je svojstvo para, a ne pojedinog dodatka, pa mora biti vidljivo uz
    oba — korisnik koji čita samo jednu stavku inače ne bi saznao za sukob.

    Vraća broj pronađenih parova.
    """
    by_name = {item.supplement_name: item for item in items}
    found = 0

    for pair, warning in interaction_warnings(by_name):
        found += 1
        for name in pair:
            item = by_name[name]
            if warning not in item.warnings:
                item.warnings.append(warning)

    return found
