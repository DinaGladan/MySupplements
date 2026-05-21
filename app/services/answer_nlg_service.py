import json
import logging

from app.prompts.answer_nlg_prompt import NLG_SYSTEM_PROMPT
from app.schemas.recommendation_schema import RecommendationItem
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


def generate_recommendation_text(
    recommendations: list[RecommendationItem],
) -> str:
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
            NLG_SYSTEM_PROMPT,
            json.dumps(serialized, ensure_ascii=False, indent=2),
        )

    except Exception as e:
        logger.warning(f"NLG generation failed: {e}")

        lines = ["Preporučeni suplementi:"]

        for rec in recommendations:
            lines.append(f"- {rec.supplement_name} (score: {rec.total_score})")

        lines.append(
            "\n Savjetujte se s liječnikom prije korištenja dodataka prehrani."
        )

        return "\n".join(lines)
