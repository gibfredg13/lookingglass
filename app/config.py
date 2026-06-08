from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Analyst Lens PoC"
    api_prefix: str = "/api/v1"
    # Default to SQLite for local dev; override with AL_DATABASE_URL for Postgres
    database_url: str = "sqlite:///./data/analyst_lens.db"

    # Auth
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_prefix="AL_", env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

