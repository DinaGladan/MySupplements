import logging

from app.prompts.goal_parser_prompt import GOALS_SYSTEM_PROMPT
from app.schemas.goals_schema import ParsedGoals
from app.services.llm_client import llm_client
from app.services.validation_service import validate_goals_data

logger = logging.getLogger(__name__)


def parse_goals(goals_text: str) -> ParsedGoals:
    try:
        data = llm_client.complete_json(GOALS_SYSTEM_PROMPT, goals_text)
        return validate_goals_data(data)
    except Exception as e:
        logger.warning(f"Goals parsing failed, returning empty goals. Error: {e}")
        return ParsedGoals(goals=[])
