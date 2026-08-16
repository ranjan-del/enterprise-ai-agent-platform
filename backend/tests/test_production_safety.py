"""Tests for the production safety rails in app.core.config.

The defaults in config.py are chosen so that cloning the repo and running one
command works with no setup. Three of them are dangerous the moment the app is
reachable from the internet: a signing secret that is printed in the source, a
demo tenant whose password is in the README, and create_all standing in for
migrations.

The rails only fire when ENVIRONMENT=production, which means they are never
exercised by ordinary local use or by the rest of the suite. Untested code that
runs exactly once, during a deploy, is the kind that turns out not to work, so
these construct Settings directly with a production environment and assert on
what comes out.
"""

import pytest

from app.core.config import MIN_SECRET_LENGTH, Settings

REAL_SECRET = "s" * MIN_SECRET_LENGTH


def production(**overrides) -> Settings:
    """Build a Settings instance as if deploying, ignoring any ambient .env."""
    values = {"ENVIRONMENT": "production", "JWT_SECRET": REAL_SECRET}
    values.update(overrides)
    return Settings(_env_file=None, **values)


class TestSigningSecret:
    @pytest.mark.parametrize(
        "placeholder", ["change-me", "change-me-for-production", "secret", ""]
    )
    def test_refuses_to_boot_on_a_placeholder_secret(self, placeholder):
        with pytest.raises(RuntimeError, match="JWT_SECRET"):
            production(JWT_SECRET=placeholder)

    def test_refuses_a_secret_that_is_merely_short(self):
        with pytest.raises(RuntimeError, match=str(MIN_SECRET_LENGTH)):
            production(JWT_SECRET="short-but-not-a-placeholder")

    def test_accepts_a_real_secret(self):
        assert production().JWT_SECRET == REAL_SECRET

    def test_placeholders_are_fine_outside_production(self):
        """The whole point of the default is that local runs need no setup."""
        settings = Settings(_env_file=None, ENVIRONMENT="development", JWT_SECRET="change-me")
        assert settings.JWT_SECRET == "change-me"


class TestForcedOffInProduction:
    def test_demo_tenant_is_not_seeded(self):
        """demo@acme.com / demopass123 is published in the README."""
        assert production(SEED_DEMO_DATA=True).SEED_DEMO_DATA is False

    def test_create_all_is_disabled_so_alembic_owns_the_schema(self):
        assert production(AUTO_CREATE_TABLES=True).AUTO_CREATE_TABLES is False

    def test_neither_is_overridden_in_development(self):
        """Outside production the rails must not touch what was asked for.

        The values are passed explicitly rather than relying on the class
        defaults, because the test suite sets SEED_DEMO_DATA=false in the
        environment and an implicit default would read that instead.
        """
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="development",
            SEED_DEMO_DATA=True,
            AUTO_CREATE_TABLES=True,
        )
        assert settings.SEED_DEMO_DATA is True
        assert settings.AUTO_CREATE_TABLES is True


def test_environment_matching_is_forgiving_about_case_and_spacing():
    with pytest.raises(RuntimeError):
        Settings(_env_file=None, ENVIRONMENT="  Production ", JWT_SECRET="change-me")
