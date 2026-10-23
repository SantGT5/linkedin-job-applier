"""Process environment for the api and worker (secrets come from `.env` via compose)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    database_url: str = "postgresql+psycopg://applier:applier@postgres:5432/applier"
    ui_password: str = ""
    session_secret: str = ""
    data_dir: str = "/data"
    # Optional secrets; only ever reported as set / not set.
    linkedin_username: str = ""
    linkedin_password: str = ""
    claude_api_key: str = ""
    glm_api_key: str = ""


@lru_cache
def get_env() -> Env:
    return Env()
