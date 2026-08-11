from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Supplement Advisor"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str = "postgresql://postgres:postgres@localhost:5432/mysupplements_db"

    llm_api_key: str | None = None
    llm_model: str = "llama3"
    llm_base_url: str = "http://localhost:11434"

    min_display_score: int = 4

    # When False (default), the explanation is built by the fast deterministic
    # template (build_explanation). Set USE_LLM_EXPLANATION=True to have the LLM
    # write the explanation instead — nicer prose, but adds ~100-200s per request
    # on a local CPU model. Recommendation quality is identical either way.
    use_llm_explanation: bool = False


settings = Settings()
