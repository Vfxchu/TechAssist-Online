from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    search_api_key: str = ""          # Tavily or Serper API key
    database_url: str = "sqlite:///./techassist.db"
    upload_dir: str = "./uploads"
    max_failed_attempts: int = 5
    solution_match_threshold: float = 0.75
    cors_allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
