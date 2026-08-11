import json
import logging
import requests
from app.config import settings

logger = logging.getLogger(__name__)


def extract_json(text: str) -> str | None:
    """
    Extract JSON object from raw LLM output.
    Handles markdown code blocks and extra text.
    """

    cleaned = text.strip().replace("```json", "").replace("```", "").strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1

    if start == -1 or end == 0:
        return None

    return cleaned[start:end]


class LLMClient:

    def __init__(self):
        self.base_url = settings.llm_base_url
        self.model = settings.llm_model

    def complete(self, system_prompt: str, user_message: str) -> str:
        """
        Generate raw completion response.
        """

        prompt = f"""
                    SYSTEM:
                    {system_prompt}

                    USER:
                    {user_message}

                    JSON:
                """

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            # Force valid JSON output from Ollama. This makes parsing far more
            # reliable (fewer retries) and lets smaller/faster models be used.
            "format": "json",
            "options": {
                "temperature": 0.1,
                "num_predict": 500,
            },
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=60,
            )

            response.raise_for_status()
            data = response.json()
            return data["response"].strip()

        except requests.RequestException as e:
            logger.error(f"Ollama request failed: {e}")
            raise

    def complete_text(self, system_prompt: str, user_message: str) -> str:
        """
        Generate natural language explanation text.
        """

        prompt = f"""
                    SYSTEM:
                    {system_prompt}

                    USER:
                    {user_message}

                    ANSWER:
                """

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 600,
            },
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                # Free-text generation is much slower than short JSON parsing;
                # on a local CPU llama3 needs well over 60s, so give it room.
                timeout=180,
            )

            response.raise_for_status()
            data = response.json()
            return data["response"].strip()

        except requests.RequestException as e:
            logger.error(f"Ollama text generation failed: {e}")
            raise

    def complete_json(
        self,
        system_prompt: str,
        user_message: str,
        retries: int = 2,
    ) -> dict:
        """
        Generate and parse JSON response.
        """

        for attempt in range(retries + 1):

            try:
                raw = self.complete(system_prompt, user_message)

                cleaned = extract_json(raw)

                if not cleaned:
                    raise ValueError("Could not extract JSON from response")

                return json.loads(cleaned)

            except (
                json.JSONDecodeError,
                ValueError,
                requests.RequestException,
            ) as e:

                logger.warning(f"LLM attempt {attempt + 1} failed: {e}")

                if attempt == retries:
                    raise


llm_client = LLMClient()
