from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Supplement Advisor"
    APP_VERSION: str = "1.0.0"
    DATABASE_URL: str = (
        "postgresql://postgres:YOUR_PASSWORD@localhost:5432/mysupplements_db"
    )

    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    MIN_RECOMMENDATION_SCORE: int = 4
    DEBUG: bool = False

    class Config:
        env_file = ".env"


settings = Settings()
