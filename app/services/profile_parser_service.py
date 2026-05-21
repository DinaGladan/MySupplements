import logging

from app.prompts.profile_parser_prompt import PROFILE_SYSTEM_PROMPT
from app.schemas.profile_schema import ParsedProfile
from app.services.llm_client import llm_client
from app.services.validation_service import validate_profile_data

logger = logging.getLogger(__name__)


def parse_profile(profile_text: str) -> ParsedProfile:
    try:
        data = llm_client.complete_json(PROFILE_SYSTEM_PROMPT, profile_text)
        return validate_profile_data(data)
    except Exception as e:
        logger.warning(f"Profile parsing failed, returning empty profile. Error: {e}")
        return ParsedProfile()
