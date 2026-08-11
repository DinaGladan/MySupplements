from app.db.database import SessionLocal, engine, Base
from app.models.supplement import Supplement

SUPPLEMENTS_DATA = [
    {
        "name": "magnesium_glycinate",
        "description": "Oblik magnezija koji se dobro apsorbira i koristi za opuštanje živčanog sustava i bolji san.",
        "goal_tags": ["better_sleep", "stress_reduction", "mood_support", "recovery"],
        "state_scores": {
            "sleep_quality:poor": 3,
            "stress_level:high": 3,
            "stress_level:medium": 1,
            "fatigue_level:high": 1,
        },
        "lifestyle_scores": {
            "activity_level:high": 2,
            "caffeine_intake:high": 1,
        },
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "omega_3",
        "description": "Esencijalne masne kiseline važne za mozak, srce i upalne procese.",
        "goal_tags": [
            "heart_health",
            "better_focus",
            "mood_support",
            "immune_support",
            "skin_health",
        ],
        "state_scores": {
            "focus_issues:true": 2,
            "stress_level:high": 1,
        },
        "lifestyle_scores": {},
        "diet_scores": {
            "fish_intake:low": 3,
            "diet_type:vegan": 2,
            "diet_type:vegetarian": 2,
        },
        "deficiency_scores": {
            "fish_intake:low": 2,
        },
        "penalties": {},
    },
    {
        "name": "vitamin_d3",
        "description": "Vitamin važan za imunitet, raspoloženje i zdravlje kostiju.",
        "goal_tags": ["immune_support", "bone_health", "mood_support"],
        "state_scores": {
            "fatigue_level:high": 1,
            "stress_level:high": 1,
        },
        "lifestyle_scores": {},
        "diet_scores": {
            "diet_type:vegan": 2,
            "diet_type:vegetarian": 1,
        },
        "deficiency_scores": {
            "sun_exposure:low": 3,
        },
        "penalties": {},
    },
    {
        "name": "vitamin_b12",
        "description": "Ključan za energiju, živčani sustav i proizvodnju crvenih krvnih stanica.",
        "goal_tags": ["more_energy", "better_focus", "general_health"],
        "state_scores": {
            "fatigue_level:high": 3,
            "focus_issues:true": 2,
        },
        "lifestyle_scores": {},
        "diet_scores": {
            "diet_type:vegan": 4,
            "diet_type:vegetarian": 2,
        },
        "deficiency_scores": {
            "diet_type:vegan": 3,
        },
        "penalties": {},
    },
    {
        "name": "ashwagandha",
        "description": "Adaptogena biljka koja smanjuje stres i balansira kortizol.",
        "goal_tags": ["stress_reduction", "mood_support", "better_sleep"],
        "state_scores": {
            "stress_level:high": 3,
            "stress_level:medium": 1,
            "fatigue_level:high": 2,
            "focus_issues:true": 1,
        },
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "melatonin",
        "description": "Hormon koji regulira ritam spavanja.",
        "goal_tags": ["better_sleep"],
        "state_scores": {
            "sleep_quality:poor": 3,
        },
        "lifestyle_scores": {
            "caffeine_intake:high": 1,
        },
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "creatine",
        "description": "Dodatak koji poboljšava snagu i oporavak mišića.",
        "goal_tags": ["physical_performance", "recovery", "more_energy"],
        "state_scores": {
            "focus_issues:true": 1,
        },
        "lifestyle_scores": {
            "activity_level:high": 3,
            "activity_level:medium": 1,
        },
        "diet_scores": {
            "diet_type:vegan": 2,
            "diet_type:vegetarian": 1,
        },
        "deficiency_scores": {},
        "penalties": {
            "activity_level:low": {
                "penalty": 2,
                "warning": "Kreatin ima smisla samo uz redovitu fizičku aktivnost.",
            },
        },
    },
    {
        "name": "protein_powder",
        "description": "Izvor proteina za oporavak i rast mišića.",
        "goal_tags": ["recovery", "physical_performance", "general_health"],
        "state_scores": {},
        "lifestyle_scores": {
            "activity_level:high": 2,
            "activity_level:medium": 1,
        },
        "diet_scores": {
            "diet_type:vegan": 2,
            "diet_type:vegetarian": 1,
        },
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "zinc",
        "description": "Mineral važan za imunitet, kožu i hormone.",
        "goal_tags": ["immune_support", "skin_health", "general_health"],
        "state_scores": {},
        "lifestyle_scores": {
            "activity_level:high": 2,
        },
        "diet_scores": {
            "diet_type:vegan": 2,
            "diet_type:vegetarian": 1,
        },
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "probiotics",
        "description": "Korisne bakterije za probavu i imunitet.",
        "goal_tags": ["immune_support", "general_health", "skin_health"],
        "state_scores": {},
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "biotin",
        "description": "Vitamin B skupine važan za kosu, kožu i nokte.",
        "goal_tags": ["hair_health", "nail_strength", "skin_health"],
        "state_scores": {},
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "collagen",
        "description": "Protein važan za kožu, kosu, nokte i zglobove.",
        "goal_tags": ["skin_health", "hair_health", "nail_strength", "recovery"],
        "state_scores": {},
        "lifestyle_scores": {
            "activity_level:high": 1,
        },
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {
            "diet_type:vegan": {
                "penalty": 4,
                "hard": True,
                "warning": "Kolagen je životinjskog porijekla i nije kompatibilan s veganskom prehranom.",
            },
            "diet_type:vegetarian": {
                "penalty": 4,
                "hard": True,
                "warning": "Kolagen se dobiva iz kože i kostiju zaklanih životinja i nije kompatibilan s vegetarijanskom prehranom.",
            },
        },
    },
    {
        "name": "l_theanine",
        "description": "Aminokiselina koja potiče opuštanje bez sedacije i poboljšava fokus.",
        "goal_tags": ["better_focus", "stress_reduction", "mood_support"],
        "state_scores": {
            "stress_level:high": 2,
            "stress_level:medium": 1,
            "focus_issues:true": 2,
        },
        "lifestyle_scores": {
            "caffeine_intake:high": 2,
        },
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "rhodiola_rosea",
        "description": "Adaptogena biljka za otpornost na stres i mentalnu energiju.",
        "goal_tags": ["stress_reduction", "more_energy", "better_focus"],
        "state_scores": {
            "stress_level:high": 2,
            "fatigue_level:high": 2,
            "focus_issues:true": 1,
        },
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "gaba",
        "description": "Neurotransmiter koji potiče smirenost i smanjuje napetost.",
        "goal_tags": ["stress_reduction", "better_sleep"],
        "state_scores": {
            "stress_level:high": 2,
            "sleep_quality:poor": 1,
        },
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "b_complex",
        "description": "Skup vitamina B važnih za živčani sustav i energiju.",
        "goal_tags": ["more_energy", "better_focus", "mood_support"],
        "state_scores": {
            "fatigue_level:high": 3,
            "fatigue_level:medium": 1,
            "focus_issues:true": 2,
            "stress_level:high": 1,
        },
        "lifestyle_scores": {
            "activity_level:high": 1,
        },
        "diet_scores": {
            "diet_type:vegan": 3,
            "diet_type:vegetarian": 2,
        },
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "lions_mane",
        "description": "Gljiva koja podupire kognitivne funkcije.",
        "goal_tags": ["better_focus", "mood_support"],
        "state_scores": {
            "focus_issues:true": 3,
        },
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "glycine",
        "description": "Aminokiselina koja poboljšava san i regeneraciju.",
        "goal_tags": ["better_sleep", "recovery"],
        "state_scores": {
            "sleep_quality:poor": 2,
        },
        "lifestyle_scores": {
            "activity_level:high": 1,
        },
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "valerian_root",
        "description": "Biljni dodatak za opuštanje i bolji san.",
        "goal_tags": ["better_sleep", "stress_reduction"],
        "state_scores": {
            "sleep_quality:poor": 2,
            "stress_level:high": 1,
        },
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "coenzyme_q10",
        "description": "Spoj koji podržava energiju i zdravlje srca.",
        "goal_tags": ["more_energy", "heart_health"],
        "state_scores": {
            "fatigue_level:high": 2,
            "fatigue_level:medium": 1,
        },
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "iron",
        "description": "Mineral važan za transport kisika u krvi.",
        "goal_tags": ["more_energy", "general_health"],
        "state_scores": {
            "fatigue_level:high": 2,
        },
        "lifestyle_scores": {
            "activity_level:high": 1,
        },
        "diet_scores": {
            "diet_type:vegan": 3,
            "diet_type:vegetarian": 2,
        },
        "deficiency_scores": {},
        "penalties": {
            "gender:male": {
                "penalty": 1,
                "warning": "Muškarci rijetko trebaju dodatno željezo bez potvrđenog deficita.",
            },
        },
    },
    {
        "name": "l_carnitine",
        "description": "Pomaže transport masti u mitohondrije za energiju.",
        "goal_tags": ["more_energy", "physical_performance"],
        "state_scores": {
            "fatigue_level:high": 1,
        },
        "lifestyle_scores": {
            "activity_level:high": 2,
            "activity_level:medium": 1,
        },
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "beta_alanine",
        "description": "Aminokiselina koja poboljšava sportske performanse.",
        "goal_tags": ["physical_performance", "recovery"],
        "state_scores": {},
        "lifestyle_scores": {
            "activity_level:high": 3,
            "activity_level:medium": 1,
        },
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {
            "activity_level:low": {
                "penalty": 3,
                "warning": "Beta-alanin je namijenjen osobama s intenzivnim treningom.",
            },
        },
    },
    {
        "name": "electrolytes",
        "description": "Minerali koji održavaju hidrataciju i mišićnu funkciju.",
        "goal_tags": ["physical_performance", "recovery"],
        "state_scores": {},
        "lifestyle_scores": {
            "activity_level:high": 3,
            "activity_level:medium": 1,
        },
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {
            "activity_level:low": {
                "penalty": 2,
                "warning": "Elektroliti su najkorisniji uz redovitu fizičku aktivnost.",
            },
        },
    },
    {
        "name": "vitamin_c",
        "description": "Antioksidans važan za imunitet.",
        "goal_tags": ["immune_support", "skin_health"],
        "state_scores": {
            "stress_level:high": 1,
        },
        "lifestyle_scores": {
            "activity_level:high": 1,
        },
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "selenium",
        "description": "Mineral koji podržava štitnjaču i imunitet.",
        "goal_tags": ["immune_support", "general_health"],
        "state_scores": {},
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "elderberry",
        "description": "Biljni dodatak za podršku imunitetu.",
        "goal_tags": ["immune_support"],
        "state_scores": {},
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "hyaluronic_acid",
        "description": "Spoj važan za hidrataciju kože.",
        "goal_tags": ["skin_health"],
        "state_scores": {},
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "silica",
        "description": "Mineral za kosu, kožu i nokte.",
        "goal_tags": ["hair_health", "skin_health", "nail_strength"],
        "state_scores": {},
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "msm",
        "description": "Spoj sa sumporom za zglobove, kosu i kožu.",
        "goal_tags": ["skin_health", "hair_health", "recovery"],
        "state_scores": {},
        "lifestyle_scores": {
            "activity_level:high": 1,
        },
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "glucosamine_chondroitin",
        "description": "Dodatak za zglobove i hrskavicu.",
        "goal_tags": ["recovery", "general_health"],
        "state_scores": {},
        "lifestyle_scores": {
            "activity_level:high": 2,
        },
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {
            "diet_type:vegan": {
                "penalty": 4,
                "hard": True,
                "warning": "Glukozamin i hondroitin nisu veganski i nisu kompatibilni s veganskom prehranom.",
            },
            "diet_type:vegetarian": {
                "penalty": 4,
                "hard": True,
                "warning": "Glukozamin i hondroitin dobivaju se iz oklopa rakova i školjki te nisu kompatibilni s vegetarijanskom prehranom.",
            },
        },
    },
    {
        "name": "calcium",
        "description": "Mineral za kosti i mišićnu funkciju.",
        "goal_tags": ["bone_health"],
        "state_scores": {},
        "lifestyle_scores": {},
        "diet_scores": {
            "diet_type:vegan": 2,
            "diet_type:vegetarian": 1,
        },
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "vitamin_k2",
        "description": "Vitamin važan za kosti i srce.",
        "goal_tags": ["bone_health", "heart_health"],
        "state_scores": {},
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "curcumin",
        "description": "Biljni ekstrakt snažnog protuupalnog i antioksidativnog djelovanja, najčešće standardiziran na kurkumin.",
        "goal_tags": ["immune_support", "recovery", "general_health", "skin_health"],
        "state_scores": {
            "fatigue_level:high": 1,
        },
        "lifestyle_scores": {
            "activity_level:high": 2,
        },
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
    {
        "name": "resveratrol",
        "description": "Polifenol iz grožđa poznat po snažnom antioksidativnom djelovanju i podršci zdravlju srca.",
        "goal_tags": [
            "heart_health",
            "general_health",
            "immune_support",
            "skin_health",
        ],
        "state_scores": {},
        "lifestyle_scores": {},
        "diet_scores": {},
        "deficiency_scores": {},
        "penalties": {},
    },
]


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        existing = db.query(Supplement).count()
        if existing > 0:
            print(f"Baza već sadrži {existing} suplemenata. Preskačem seed.")
            return

        for item in SUPPLEMENTS_DATA:
            supplement = Supplement(**item)
            db.add(supplement)

        db.commit()
        print(f"Uneseno {len(SUPPLEMENTS_DATA)} suplemenata u bazu.")

    except Exception as e:
        db.rollback()
        print(f"Greška pri seeding: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
