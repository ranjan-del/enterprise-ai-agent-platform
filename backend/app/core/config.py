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

# Placeholder secrets that ship in source control and compose files. None of
# them may ever sign a real token: anyone who has read the repository could
# mint themselves an owner token for any organization on the platform.
INSECURE_SECRETS = {"change-me", "change-me-for-production", "secret", ""}

# Minimum acceptable length for a production signing secret.
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    # --- App ---------------------------------------------------------------
    APP_NAME: str = "Enterprise AI Agent Platform"
    ENVIRONMENT: str = "development"

    # --- Database ----------------------------------------------------------
    # Local default = SQLite (no install needed). Docker overrides with Postgres.
    DATABASE_URL: str = "sqlite:///./platform.db"

    # Create missing tables from the models at startup. Fine locally and in the
    # test suite, wrong anywhere real: create_all only ever ADDS tables, so a
    # changed column is silently skipped and the app then queries a schema the
    # database does not have. Alembic owns the schema instead
    # (`alembic upgrade head`), and production forces this off below.
    AUTO_CREATE_TABLES: bool = True

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

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() == "production"

    def model_post_init(self, __context) -> None:
        """Apply production safety rails as soon as settings load.

        Three defaults in this file are exactly right for someone cloning the
        repo and running it in one command, and indefensible on a public URL:
        a signing secret printed in the source, a demo tenant seeded with a
        published password, and create_all standing in for migrations. Rather
        than trusting whoever deploys to remember all three, the first is a
        refusal to boot and the other two are forced off.
        """
        if not self.is_production:
            return

        # A forgeable signing secret is a complete auth bypass across every
        # tenant, so this one fails loudly rather than being quietly corrected.
        if self.JWT_SECRET.strip() in INSECURE_SECRETS:
            raise RuntimeError(
                "JWT_SECRET is still a placeholder value while ENVIRONMENT=production. "
                "Set a real secret, e.g. "
                'python -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        if len(self.JWT_SECRET) < MIN_SECRET_LENGTH:
            raise RuntimeError(
                f"JWT_SECRET must be at least {MIN_SECRET_LENGTH} characters in production "
                f"(got {len(self.JWT_SECRET)})."
            )

        # demo@acme.com / demopass123 is in the README. Seeding it on a public
        # deployment hands every reader a working account inside a live org.
        self.SEED_DEMO_DATA = False

        # Schema changes go through Alembic in production. Leaving create_all
        # on would mask a forgotten migration: the app boots, a new table
        # appears, an altered column does not, and the failure surfaces later
        # as a query error against real data.
        self.AUTO_CREATE_TABLES = False


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the environment is parsed only once."""
    return Settings()


settings = get_settings()
