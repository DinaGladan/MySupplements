import logging
from app.services.llm_client import llm_client
from app.schemas.goals_schema import ParsedGoals

logger = logging.getLogger(__name__)

GOALS_SYSTEM_PROMPT = """
You are a goal extraction assistant. Extract the user's health and wellness goals from free text.

Return ONLY a valid JSON object. No explanation, no markdown, no extra text.

Rules:
- Use only goals from the allowed list below
- Return an empty list if no clear goal is found
- No duplicates
- A user can have multiple goals

Allowed goals:
better_sleep, stress_reduction, mood_support, more_energy, better_focus,
recovery, immune_support, physical_performance, heart_health, bone_health,
hair_health, skin_health, nail_strength, general_health

JSON schema:
{
  "goals": ["<goal1>", "<goal2>"]
}
""".strip()


def parse_goals(goals_text: str) -> ParsedGoals:
    """Parse free-text goals into a structured ParsedGoals."""
    try:
        data = llm_client.complete_json(GOALS_SYSTEM_PROMPT, goals_text)
        return ParsedGoals(**data)
    except Exception as e:
        logger.warning(f"Goals parsing failed, returning empty goals. Error: {e}")
        return ParsedGoals(goals=[])
