"""
config.py — Application settings loaded from environment variables.
Uses Pydantic BaseSettings so every value is validated at startup.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    openai_api_key: str
    redis_url: str = "redis://localhost:6379"
    model_name: str = "gpt-4o-mini"
    allowed_origins: str = "http://localhost:3000,https://*.vercel.app"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
