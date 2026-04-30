from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path


_ROOT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    # OpenAI – loaded from root .env
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o"

    # App
    debug: bool = True
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Verification settings
    self_consistency_samples: int = 3
    self_consistency_temperature: float = 0.7
    max_critique_loops: int = 3

    model_config = {
        "env_file": str(_ROOT_ENV),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
