from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Supplement Advisor"
    app_version: str = "1.0.0"
    debug: bool = False

    database_url: str = "postgresql://postgres:postgres@localhost:5432/mysupplements_db"

    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"

    min_display_score: int = 4

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
