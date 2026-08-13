"""
build_scenarios.py — sastavlja data/scenarios.json iz definicija niže.

Polje `forbidden` se ne upisuje ručno nego izvodi iz stvarnih tvrdih pravila u
bazi znanja, pa ne može odlutati od `app/db/seed.py`.

Polje `relevant` ostaje PRAZNO. Ono je predmet neovisnog označavanja (A3) i ne
smije se izvesti iz pravila bodovanja — inače ostaje kružnost zbog koje A3 i
postoji. Popunjava se skriptom merge_annotations.py kad označivači vrate listiće.

    python evaluation/build_scenarios.py
"""

from __future__ import annotations

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from app.db.seed import SUPPLEMENTS_DATA  # noqa: E402
from app.schemas.profile_schema import ParsedProfile  # noqa: E402
from app.services.scoring_service import _profile_tokens, contraindications  # noqa: E402

DATA_DIR = os.path.join(SCRIPT_DIR, "data")
PROFILE_FIELDS = list(ParsedProfile.model_fields)


def S(sid, tags, profile_text, goals_text, profile, goals, expected_empty=False):
    return {
        "id": sid,
        "tags": tags,
        "profile_text": profile_text,
        "goals_text": goals_text,
        "expected_profile": profile,
        "expected_goals": goals,
        "expected_empty": expected_empty,
    }


SCENARIOS = [
    # ---------------------------------------------------------------- baseline
    S("S01", ["baseline"],
      "Imam 23 godine, vegetarijanka sam, san mi je u redu ali sam često pod stresom, "
      "tijekom dana sam umorna, teško se koncentriram, pijem puno kave i malo sam na suncu.",
      "Želim bolje spavati, imati više energije i smanjiti stres.",
      {"age": 23, "gender": "female", "sleep_quality": "average", "stress_level": "medium",
       "diet_type": "vegetarian", "caffeine_intake": "high", "sun_exposure": "low",
       "fatigue_level": "medium", "focus_issues": True},
      ["better_sleep", "more_energy", "stress_reduction"]),

    S("S02", ["baseline"],
      "Vegan sam i cijeli dan se osjećam iscrpljeno.",
      "Želim više energije.",
      {"diet_type": "vegan", "fatigue_level": "high"},
      ["more_energy"]),

    S("S03", ["baseline"],
      "Imam 27 godina, treniram intenzivno gotovo svaki dan.",
      "Želim bolji oporavak i bolju fizičku izvedbu.",
      {"age": 27, "activity_level": "high"},
      ["recovery", "physical_performance"]),

    S("S04", ["baseline"],
      "Gotovo nikada ne jedem ribu.",
      "Želim podržati zdravlje srca.",
      {"fish_intake": "low"},
      ["heart_health"]),

    S("S05", ["baseline"],
      "Radim u uredu i rijetko izlazim na sunce, zimi mi padne raspoloženje.",
      "Želim jači imunitet i bolje raspoloženje.",
      {"sun_exposure": "low"},
      ["immune_support", "mood_support"]),

    S("S06", ["baseline"],
      "Imam 34 godine, stalno sam umoran i teško se koncentriram na poslu.",
      "Želim više energije i bolju koncentraciju.",
      {"age": 34, "fatigue_level": "high", "focus_issues": True},
      ["more_energy", "better_focus"]),

    S("S07", ["baseline"],
      "Vrlo loše spavam, pod velikim sam stresom i pijem puno kave.",
      "Želim bolje spavati i smanjiti stres.",
      {"sleep_quality": "poor", "stress_level": "high", "caffeine_intake": "high"},
      ["better_sleep", "stress_reduction"]),

    S("S08", ["baseline"],
      "Imam 29 godina, jedem sve, ali koža mi je loša i nokti mi pucaju.",
      "Želim zdraviju kožu, jaču kosu i jače nokte.",
      {"age": 29, "diet_type": "omnivore"},
      ["skin_health", "hair_health", "nail_strength"]),

    # ---------------------------------------------------------------- negacija
    S("S09", ["negation"],
      "Ne pijem kavu i nikada je nisam pila.",
      "Želim bolje spavati.",
      {"caffeine_intake": "low"},
      ["better_sleep"]),

    S("S10", ["negation"],
      "Nemam problema sa snom, spavam odlično, ali sam preko dana umorna.",
      "Želim više energije.",
      {"sleep_quality": "good", "fatigue_level": "high"},
      ["more_energy"]),

    S("S11", ["negation", "safety"],
      "Imam 31 godinu, nisam trudna i ne dojim, ali sam pod stresom.",
      "Želim smanjiti stres.",
      {"age": 31, "stress_level": "high", "pregnancy": False, "breastfeeding": False},
      ["stress_reduction"]),

    S("S12", ["negation", "safety"],
      "Nemam nikakvih alergija, jedem ribu redovito.",
      "Želim podržati srce.",
      {"fish_intake": "high"},
      ["heart_health"]),

    # ------------------------------------------------- hrvatski bez dijakritike
    S("S13", ["no_diacritics"],
      "Cesto sam pod stresom i lose spavam.",
      "Zelim smanjiti stres i bolje spavati.",
      {"stress_level": "high", "sleep_quality": "poor"},
      ["stress_reduction", "better_sleep"]),

    S("S14", ["no_diacritics"],
      "Imam 26 godina, vegetarijanka sam i slabo izlazim na sunce.",
      "Zelim jaci imunitet.",
      {"age": 26, "gender": "female", "diet_type": "vegetarian", "sun_exposure": "low"},
      ["immune_support"]),

    S("S15", ["no_diacritics"],
      "Puno treniram, aktivnost mi je visoka, stalno sam umoran.",
      "Zelim bolji oporavak i vise energije.",
      {"activity_level": "high", "fatigue_level": "high"},
      ["recovery", "more_energy"]),

    S("S16", ["no_diacritics", "safety"],
      "Imam 33 godine, alergicna sam na mlijeko i intenzivno treniram.",
      "Zelim bolji oporavak.",
      {"age": 33, "activity_level": "high", "allergies": ["milk"]},
      ["recovery"]),

    # -------------------------------------------------------- miješani jezik
    S("S17", ["code_switching"],
      "Imam 25 godina, I am vegan, često sam pod stresom.",
      "Želim stress reduction i više energije.",
      {"age": 25, "diet_type": "vegan", "stress_level": "high"},
      ["stress_reduction", "more_energy"]),

    S("S18", ["code_switching", "safety"],
      "I am 30 years old, vegetarijanka sam i trudna sam.",
      "I want better sleep i manje stresa.",
      {"age": 30, "gender": "female", "diet_type": "vegetarian", "pregnancy": True},
      ["better_sleep", "stress_reduction"]),

    S("S19", ["code_switching"],
      "Trebam more energy, stalno sam tired i teško se fokusiram.",
      "More energy and better focus.",
      {"fatigue_level": "high", "focus_issues": True},
      ["more_energy", "better_focus"]),

    # ------------------------------------------------------------- tipfeleri
    S("S20", ["typos"],
      "Imam 27 godina i tesko se koncentiram na poslu.",
      "Zelim bolju koncentracju.",
      {"age": 27, "focus_issues": True},
      ["better_focus"]),

    S("S21", ["typos"],
      "Imam problema sa snom, stalo sam umorna i pijem puuno kave.",
      "Zelim bolje spavti.",
      {"sleep_quality": "poor", "fatigue_level": "high", "caffeine_intake": "high"},
      ["better_sleep"]),

    S("S22", ["typos", "safety"],
      "Vegetarjanka sam, imam 24 godne.",
      "Zelim zdraviju kozu i jace nokte.",
      {"age": 24, "gender": "female", "diet_type": "vegetarian"},
      ["skin_health", "nail_strength"]),

    # ------------------------------------------------------ kontraindikacije
    S("S23", ["safety"],
      "Imam 25 godina, veganka sam i intenzivno treniram.",
      "Želim zdraviju kožu, jaču kosu, jače nokte i bolji oporavak.",
      {"age": 25, "gender": "female", "diet_type": "vegan", "activity_level": "high"},
      ["skin_health", "hair_health", "nail_strength", "recovery"]),

    S("S24", ["safety"],
      "Imam 30 godina, vegetarijanka sam i ne vježbam puno.",
      "Želim zdraviju kožu, jaču kosu, jače nokte i bolji oporavak.",
      {"age": 30, "gender": "female", "diet_type": "vegetarian", "activity_level": "low"},
      ["skin_health", "hair_health", "nail_strength", "recovery"]),

    S("S25", ["safety"],
      "Imam 26 godina i jako sam alergična na ribu.",
      "Želim podržati srce i koncentraciju.",
      {"age": 26, "gender": "female", "allergies": ["fish"]},
      ["heart_health", "better_focus"]),

    S("S26", ["safety"],
      "Imam 45 godina, alergičan sam na plodove mora, bole me zglobovi.",
      "Želim bolji oporavak i opće zdravlje.",
      {"age": 45, "gender": "male", "allergies": ["shellfish"]},
      ["recovery", "general_health"]),

    S("S27", ["safety"],
      "Imam 22 godine, ne podnosim mlijeko, treniram svaki dan.",
      "Želim bolju fizičku izvedbu i oporavak.",
      {"age": 22, "activity_level": "high", "allergies": ["milk"]},
      ["physical_performance", "recovery"]),

    S("S28", ["safety"],
      "Imam 38 godina, alergična sam na gljive i teško se koncentriram.",
      "Želim bolju koncentraciju i raspoloženje.",
      {"age": 38, "gender": "female", "allergies": ["mushroom"], "focus_issues": True},
      ["better_focus", "mood_support"]),

    S("S29", ["safety"],
      "Imam 31 godinu, trudna sam, pod stresom sam i loše spavam.",
      "Želim smanjiti stres i bolje spavati.",
      {"age": 31, "gender": "female", "pregnancy": True,
       "stress_level": "high", "sleep_quality": "poor"},
      ["stress_reduction", "better_sleep"]),

    S("S30", ["safety"],
      "Imam 29 godina, dojim bebu, iscrpljena sam i pod stresom.",
      "Želim više energije i manje stresa.",
      {"age": 29, "gender": "female", "breastfeeding": True,
       "fatigue_level": "high", "stress_level": "high"},
      ["more_energy", "stress_reduction"]),

    S("S31", ["safety"],
      "Imam 32 godine, veganka sam i trudna, malo sam na suncu.",
      "Želim jači imunitet, zdravlje kostiju i manje stresa.",
      {"age": 32, "gender": "female", "diet_type": "vegan", "pregnancy": True,
       "sun_exposure": "low"},
      ["immune_support", "bone_health", "stress_reduction"]),

    S("S32", ["safety"],
      "Imam 28 godina, veganka sam i alergična na ribu.",
      "Želim podržati srce, kožu i opće zdravlje.",
      {"age": 28, "gender": "female", "diet_type": "vegan", "allergies": ["fish"]},
      ["heart_health", "skin_health", "general_health"]),

    # ------------------------------------------------------- prazan rezultat
    S("S33", ["empty"],
      "Imam 40 godina.",
      "Želim zdravlje kostiju.",
      {"age": 40},
      ["bone_health"], expected_empty=True),

    S("S34", ["empty"],
      "Ništa posebno, osjećam se dobro.",
      "Zanima me opće zdravlje.",
      {},
      ["general_health"], expected_empty=True),
]


def normalise_profile(profile: dict) -> dict:
    """Sva polja izričito, s null za ono što tekst ne spominje.

    Bez toga evaluacija ne bi mogla razlikovati polje koje je model ispravno
    ostavio praznim od polja koje uopće nije ocijenjeno."""
    return {field: profile.get(field) for field in PROFILE_FIELDS}


def derive_forbidden(profile: dict) -> list[str]:
    """Tvrde kontraindikacije koje ovaj profil aktivira, izravno iz baze znanja."""
    tokens = _profile_tokens(ParsedProfile(**profile))

    class _S:
        def __init__(self, d):
            self.__dict__.update(d)

    return sorted(
        item["name"]
        for item in SUPPLEMENTS_DATA
        if contraindications(_S(item), tokens)
    )


def main() -> None:
    schema = json.load(open(os.path.join(DATA_DIR, "nlu_schema.json"), encoding="utf-8"))
    allowed_goals = set(schema["goal_tags"])

    out = []
    for scenario in SCENARIOS:
        profile = scenario["expected_profile"]

        unknown = set(scenario["expected_goals"]) - allowed_goals
        if unknown:
            raise SystemExit(f"{scenario['id']}: nepoznati ciljevi {unknown}")

        ParsedProfile(**profile)  # pukne odmah ako je vrijednost izvan sheme

        out.append({
            **scenario,
            "expected_profile": normalise_profile(profile),
            "forbidden": derive_forbidden(profile),
            "relevant": [],
        })

    path = os.path.join(DATA_DIR, "scenarios.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    tags = {}
    for scenario in out:
        for tag in scenario["tags"]:
            tags[tag] = tags.get(tag, 0) + 1

    with_forbidden = sum(1 for s in out if s["forbidden"])
    print(f"Zapisano {len(out)} scenarija u {path}")
    print(f"  po oznakama : {dict(sorted(tags.items()))}")
    print(f"  s tvrdim kontraindikacijama: {with_forbidden}")
    print(f"  relevant popunjen: {sum(1 for s in out if s['relevant'])}/{len(out)}"
          f"  <- popunjava se tek neovisnim označavanjem (A3)")


if __name__ == "__main__":
    main()
