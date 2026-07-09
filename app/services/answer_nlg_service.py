import json
import logging

from app.prompts.answer_nlg_prompt import build_nlg_system_prompt
from app.schemas.recommendation_schema import RecommendationItem
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


# --- Language display maps for the deterministic (fallback) explanation ------

# GoalType value -> phrase, per language.
_GOAL_LABELS = {
    "hr": {
        "better_sleep": "bolji san",
        "stress_reduction": "smanjenje stresa",
        "mood_support": "bolje raspoloženje",
        "more_energy": "više energije",
        "better_focus": "bolji fokus",
        "recovery": "oporavak",
        "immune_support": "jačanje imuniteta",
        "physical_performance": "fizičke performanse",
        "heart_health": "zdravlje srca",
        "bone_health": "zdravlje kostiju",
        "hair_health": "zdravlje kose",
        "skin_health": "zdravlje kože",
        "nail_strength": "jače nokte",
        "general_health": "opće zdravlje",
    },
    "en": {
        "better_sleep": "better sleep",
        "stress_reduction": "stress reduction",
        "mood_support": "mood support",
        "more_energy": "more energy",
        "better_focus": "better focus",
        "recovery": "recovery",
        "immune_support": "immune support",
        "physical_performance": "physical performance",
        "heart_health": "heart health",
        "bone_health": "bone health",
        "hair_health": "hair health",
        "skin_health": "skin health",
        "nail_strength": "nail strength",
        "general_health": "general health",
    },
}

# "field:value" token (from a reason) -> phrase used after "because it matches".
_STATE_LABELS = {
    "hr": {
        "sleep_quality:poor": "lošoj kvaliteti sna",
        "sleep_quality:average": "prosječnoj kvaliteti sna",
        "stress_level:high": "visokoj razini stresa",
        "stress_level:medium": "povišenoj razini stresa",
        "fatigue_level:high": "izraženom umoru",
        "fatigue_level:medium": "umoru tijekom dana",
        "focus_issues:true": "problemima s fokusom",
        "caffeine_intake:high": "povećanom unosu kofeina",
        "sun_exposure:low": "slaboj izloženosti suncu",
        "fish_intake:low": "niskom unosu ribe",
        "diet_type:vegan": "veganskoj prehrani",
        "diet_type:vegetarian": "vegetarijanskoj prehrani",
        "activity_level:high": "visokoj razini aktivnosti",
    },
    "en": {
        "sleep_quality:poor": "poor sleep quality",
        "sleep_quality:average": "average sleep quality",
        "stress_level:high": "a high stress level",
        "stress_level:medium": "an elevated stress level",
        "fatigue_level:high": "significant fatigue",
        "fatigue_level:medium": "daytime fatigue",
        "focus_issues:true": "focus difficulties",
        "caffeine_intake:high": "a high caffeine intake",
        "sun_exposure:low": "low sun exposure",
        "fish_intake:low": "a low fish intake",
        "diet_type:vegan": "a vegan diet",
        "diet_type:vegetarian": "a vegetarian diet",
        "activity_level:high": "a high activity level",
    },
}

# Short static strings, per language.
_TEXT = {
    "hr": {
        "conjunction": "i",
        "intro_top": "Na temelju unesenog profila, najrelevantniji suplementi su {names}.",
        "goals": " Preporuke su povezane s navedenim ciljevima: {goals}.",
        "highlight": " Posebno se ističe {name} jer odgovara {phrases}.",
        "list_header": "Preporučeni suplementi:",
        "score_word": "rezultat",
        "no_warnings": "nema posebnih upozorenja.",
        "warnings_word": "Upozorenja:",
        "disclaimer": (
            "Napomena: prije korištenja dodataka prehrani savjetujte se s "
            "liječnikom ili stručnom osobom."
        ),
        "empty": (
            "Na temelju unesenih podataka nije pronađena nijedna dovoljno "
            "relevantna preporuka. Pokušajte detaljnije opisati svoj profil i "
            "ciljeve."
        ),
    },
    "en": {
        "conjunction": "and",
        "intro_top": "Based on the profile you provided, the most relevant supplements are {names}.",
        "goals": " These recommendations are connected to your stated goals: {goals}.",
        "highlight": " {name} stands out in particular because it matches {phrases}.",
        "list_header": "Recommended supplements:",
        "score_word": "score",
        "no_warnings": "no specific warnings.",
        "warnings_word": "Warnings:",
        "disclaimer": (
            "Note: consult a doctor or a qualified professional before using "
            "dietary supplements."
        ),
        "empty": (
            "Based on the information provided, no sufficiently relevant "
            "recommendation was found. Try describing your profile and goals in "
            "more detail."
        ),
    },
}


def _lang(language: str) -> str:
    """Normalise to a supported language code, defaulting to Croatian."""
    return language if language in _TEXT else "hr"


def _join(items: list[str], language: str) -> str:
    """Join a list into an enumeration: 'a, b i c' / 'a, b and c'."""
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    conj = _TEXT[language]["conjunction"]
    return f"{', '.join(items[:-1])} {conj} {items[-1]}"


def _reason_phrases(rec: RecommendationItem, language: str) -> list[str]:
    """
    Turn a recommendation's non-goal reasons into phrases, e.g.
    'Matches lifestyle: caffeine_intake:high' -> 'a high caffeine intake'.
    Order is preserved and duplicates removed.
    """
    phrases: list[str] = []
    for reason in rec.reasons:
        if reason.startswith("Matches goal"):
            continue
        token = reason.split(": ", 1)[-1].strip()
        phrase = _STATE_LABELS[language].get(token)
        if phrase and phrase not in phrases:
            phrases.append(phrase)
    return phrases


def build_explanation(
    recommendations: list[RecommendationItem],
    language: str = "hr",
) -> str:
    """
    Build a clean, human-readable explanation directly from the structured
    recommendation data, in the given language ("hr" or "en"). Deterministic and
    always available, so it is used as a fallback whenever the LLM explanation
    cannot be generated.
    """
    language = _lang(language)
    txt = _TEXT[language]

    if not recommendations:
        return txt["empty"] + "\n\n" + txt["disclaimer"]

    # Intro: name the top 3 supplements.
    top_names = [rec.supplement_name for rec in recommendations[:3]]
    intro = txt["intro_top"].format(names=_join(top_names, language))

    # Goals that actually drove the recommendations (first-appearance order).
    goal_labels: list[str] = []
    for rec in recommendations:
        for goal in rec.matched_goals:
            label = _GOAL_LABELS[language].get(goal.value, goal.value)
            if label not in goal_labels:
                goal_labels.append(label)
    if goal_labels:
        intro += txt["goals"].format(goals=_join(goal_labels, language))

    # Highlight the single best recommendation and why it stands out.
    top = recommendations[0]
    top_phrases = _reason_phrases(top, language)
    if top_phrases:
        intro += txt["highlight"].format(
            name=top.supplement_name, phrases=_join(top_phrases, language)
        )

    # List every recommendation with its score and any warnings.
    lines = ["", txt["list_header"]]
    for rec in recommendations:
        if rec.warnings:
            note = txt["warnings_word"] + " " + " ".join(rec.warnings)
        else:
            note = txt["no_warnings"]
        lines.append(
            f"- {rec.supplement_name} ({txt['score_word']}: {rec.total_score}) — {note}"
        )

    return "\n".join([intro, *lines, "", txt["disclaimer"]])


def generate_recommendation_text(
    recommendations: list[RecommendationItem],
    language: str = "hr",
) -> str:
    """
    Generate the natural-language explanation for a set of recommendations, in
    the given language ("hr" or "en") which follows the language of the user's
    original input.

    Primary path: the LLM (Ollama) writes the explanation. If the LLM is
    unavailable or fails (Ollama not running, timeout, invalid response), fall
    back to build_explanation(), which produces the explanation from the same
    data without any LLM call.
    """
    language = _lang(language)

    try:
        serialized = []

        for rec in recommendations:
            serialized.append(
                {
                    "supplement_name": rec.supplement_name,
                    "total_score": rec.total_score,
                    "matched_goals": [goal.value for goal in rec.matched_goals],
                    "reasons": rec.reasons,
                    "warnings": rec.warnings,
                }
            )

        return llm_client.complete_text(
            build_nlg_system_prompt(language),
            json.dumps(serialized, ensure_ascii=False, indent=2),
        )

    except Exception as e:
        logger.warning(f"NLG generation failed, using built-in explanation: {e}")
        return build_explanation(recommendations, language)
