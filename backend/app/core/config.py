"""Application settings loaded from environment via pydantic-settings.

TODO: checklist "Backend: FastAPI services + PostgreSQL + Redis" —
populate real config, secrets management, and per-environment overrides.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object. Values are placeholders only."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Enterprise AI Agent Platform"
    environment: str = "development"

    # Auth — TODO: checklist "Auth + multi-tenancy: JWT"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Datastores — TODO: checklist "PostgreSQL + Redis"
    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/platform"
    redis_url: str = "redis://redis:6379/0"

    # Vector store — TODO: checklist "vector store (Qdrant/pgvector)"
    vector_url: str = "http://qdrant:6333"


# TODO: cache with lru_cache once real config loading is implemented.
settings = Settings()
