import json
import logging
import requests
from app.config import settings

logger = logging.getLogger(__name__)


def clean_json_response(raw: str) -> str:
    cleaned = raw.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json") :].strip()

    if cleaned.startswith("```"):
        cleaned = cleaned[len("```") :].strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return cleaned


class LLMClient:
    """Wrapper for calling the LLM API."""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self.base_url = settings.LLM_BASE_URL

    def complete(self, system_prompt: str, user_message: str) -> str:
        """Send a prompt to the LLM and return the raw text response."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
        }
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except requests.RequestException as e:
            logger.error(f"LLM API request failed: {e}")
            raise

    def complete_json(self, system_prompt: str, user_message: str) -> dict:
        """Call LLM and parse the response as JSON."""
        raw = self.complete(system_prompt, user_message)
        # Strip markdown fences if present
        cleaned = clean_json_response(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM JSON response: {e}\nRaw: {raw}")
            raise


llm_client = LLMClient()
