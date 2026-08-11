"""Labeled evaluation scenarios for MySupplements.

Each scenario has:
- id / description
- profile_text, goals_text          (raw input, used by the end-to-end mode)
- gold_profile                      (the fields we expect the parser to extract)
- gold_goals                        (the goals we expect the parser to extract)
- expected_supplements              (supplements that SHOULD appear in the
                                     ranked results for this profile/goals)

The engine mode uses gold_profile + gold_goals directly (no LLM) to measure the
quality of the rule-based recommendation logic. The end-to-end mode sends the
raw text through the API and additionally measures how well the LLM parsed it.
"""

SCENARIOS = [
    {
        "id": "poor_sleep_stress",
        "description": "Poor sleep + high stress + coffee",
        "profile_text": (
            "I sleep very poorly, I am under a lot of stress and I drink a lot of coffee."
        ),
        "goals_text": "I want to sleep better and reduce stress.",
        "gold_profile": {
            "sleep_quality": "poor",
            "stress_level": "high",
            "caffeine_intake": "high",
        },
        "gold_goals": ["better_sleep", "stress_reduction"],
        "expected_supplements": {"magnesium_glycinate", "ashwagandha"},
    },
    {
        "id": "vegan_energy",
        "description": "Vegan, tired, wants energy",
        "profile_text": "I am vegan and I feel very tired during the day.",
        "goals_text": "I want more energy.",
        "gold_profile": {"diet_type": "vegan", "fatigue_level": "high"},
        "gold_goals": ["more_energy"],
        "expected_supplements": {"vitamin_b12", "b_complex"},
    },
    {
        "id": "high_activity_recovery",
        "description": "Athlete, high activity, recovery + performance",
        "profile_text": "I train intensively every day, my activity level is very high.",
        "goals_text": "I want better recovery and physical performance.",
        "gold_profile": {"activity_level": "high"},
        "gold_goals": ["recovery", "physical_performance"],
        "expected_supplements": {"creatine", "protein_powder"},
    },
    {
        "id": "low_fish_heart",
        "description": "Low fish intake, heart health goal",
        "profile_text": "I almost never eat fish.",
        "goals_text": "I want to support my heart health.",
        "gold_profile": {"fish_intake": "low"},
        "gold_goals": ["heart_health"],
        "expected_supplements": {"omega_3"},
    },
    {
        "id": "low_sun_immune",
        "description": "Low sun exposure, immune support",
        "profile_text": "I spend very little time in the sun.",
        "goals_text": "I want to strengthen my immune system.",
        "gold_profile": {"sun_exposure": "low"},
        "gold_goals": ["immune_support"],
        "expected_supplements": {"vitamin_d3"},
    },
    {
        "id": "focus_fatigue",
        "description": "Focus problems and fatigue",
        "profile_text": "I struggle to focus and I feel tired all day.",
        "goals_text": "I want better focus and more energy.",
        "gold_profile": {"focus_issues": True, "fatigue_level": "high"},
        "gold_goals": ["better_focus", "more_energy"],
        "expected_supplements": {"b_complex", "vitamin_b12"},
    },
    {
        "id": "vegan_beauty_penalty",
        "description": "Vegan wants skin/hair/nails - collagen must be penalized",
        "profile_text": "I am vegan and I care about my skin, hair and nails.",
        "goals_text": "I want healthier skin, hair and stronger nails.",
        "gold_profile": {"diet_type": "vegan"},
        "gold_goals": ["skin_health", "hair_health", "nail_strength"],
        "expected_supplements": {"biotin", "silica"},
        # collagen and glucosamine_chondroitin must NOT be recommended here.
        "forbidden_supplements": {"collagen", "glucosamine_chondroitin"},
    },
    {
        "id": "multi_goal_no_profile",
        "description": "Several goals, almost no profile detail",
        "profile_text": "I would just like to feel better overall.",
        "goals_text": "I want better sleep, stress reduction and mood support.",
        "gold_profile": {},
        "gold_goals": ["better_sleep", "stress_reduction", "mood_support"],
        "expected_supplements": {"magnesium_glycinate", "ashwagandha"},
    },
    {
        "id": "single_goal_threshold",
        "description": "One goal, no profile - should produce few/no results",
        "profile_text": "No details.",
        "goals_text": "I want better sleep.",
        "gold_profile": {},
        "gold_goals": ["better_sleep"],
        # A single goal alone = 2 points < MIN_DISPLAY_SCORE (4), so nothing qualifies.
        "expected_supplements": set(),
        "expect_empty": True,
    },
]
