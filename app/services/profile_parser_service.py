import logging
from app.services.llm_client import llm_client
from app.schemas.profile_schema import ParsedProfile

logger = logging.getLogger(__name__)

PROFILE_SYSTEM_PROMPT = """
You are a data extraction assistant. Your ONLY job is to extract structured profile data from free text.

Return ONLY a valid JSON object. No explanation, no markdown, no extra text.

Rules:
- Use null for any field not explicitly mentioned or clearly inferable
- Use only the allowed enum values listed below
- Never invent or guess values not supported by the text
- age must be a positive integer if mentioned

JSON schema to fill:
{
  "age": <int or null>,
  "gender": <"male" | "female" | null>,
  "sleep_quality": <"poor" | "average" | "good" | null>,
  "stress_level": <"low" | "medium" | "high" | null>,
  "activity_level": <"low" | "medium" | "high" | null>,
  "diet_type": <"omnivore" | "vegetarian" | "vegan" | "pescatarian" | null>,
  "fish_intake": <"low" | "medium" | "high" | null>,
  "caffeine_intake": <"low" | "medium" | "high" | null>,
  "sun_exposure": <"low" | "medium" | "high" | null>,
  "fatigue_level": <"low" | "medium" | "high" | null>,
  "focus_issues": <true | false | null>
}
""".strip()


def parse_profile(profile_text: str) -> ParsedProfile:
    """Parse free-text user profile into a structured ParsedProfile."""
    try:
        data = llm_client.complete_json(PROFILE_SYSTEM_PROMPT, profile_text)
        return ParsedProfile(**data)
    except Exception as e:
        logger.warning(f"Profile parsing failed, returning empty profile. Error: {e}")
        return ParsedProfile()
