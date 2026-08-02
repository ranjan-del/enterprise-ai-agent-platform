"""Application configuration.

Settings are read from environment variables (see backend/.env.example). The
platform is offline-first: every default lets the app boot, run, and be tested
with zero external services.

- DATABASE_URL defaults to a local SQLite file, so no PostgreSQL is required for
  development or CI. docker-compose overrides it with a PostgreSQL URL.
- REDIS_URL is optional. When empty or unreachable, session memory transparently
  falls back to an in-process store (see app.cache.redis).
- No LLM/provider API key is ever required: the agent runtime uses a
  deterministic offline responder.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---------------------------------------------------------------
    APP_NAME: str = "Enterprise AI Agent Platform"
    ENVIRONMENT: str = "development"

    # --- Database ----------------------------------------------------------
    # Local default = SQLite (no install needed). Docker overrides with Postgres.
    DATABASE_URL: str = "sqlite:///./platform.db"

    # --- Auth (JWT) --------------------------------------------------------
    JWT_SECRET: str = "change-me"  # MUST be overridden in production
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # --- Cache / session memory -------------------------------------------
    # Optional. Empty or unreachable -> in-process fallback is used.
    REDIS_URL: str = ""

    # --- CORS --------------------------------------------------------------
    CORS_ORIGINS: str = "http://localhost:4200"

    # --- Tools -------------------------------------------------------------
    # Root of the sandboxed workspace used by the file-system tool. Each tenant
    # gets its own subdirectory underneath and can never escape it.
    WORKSPACE_ROOT: str = "./workspace_data"
    # Network-backed tools (weather, github) are OFF by default so the whole
    # platform stays runnable and testable with no internet access at all.
    ALLOW_NETWORK_TOOLS: bool = False
    NETWORK_TIMEOUT_SECONDS: float = 5.0

    # --- Demo seed ---------------------------------------------------------
    # A demo org + user seeded on startup so the platform is usable immediately.
    SEED_DEMO_DATA: bool = True
    DEMO_ORG_NAME: str = "Acme Inc"
    DEMO_EMAIL: str = "demo@acme.com"
    DEMO_PASSWORD: str = "demopass123"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS is a comma-separated string; expose it as a list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the environment is parsed only once."""
    return Settings()


settings = get_settings()
