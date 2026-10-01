"""Environment-based configuration for WaxPrep.

This module intentionally contains only generic configuration handling.
Application-specific settings are introduced when the corresponding
capability is built.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os


ENVIRONMENT_VARIABLE = "WAXPREP_ENV"

ALLOWED_ENVIRONMENTS = frozenset(
    {
        "development",
        "test",
        "production",
    }
)


class ConfigurationError(ValueError):
    """Raised when WaxPrep configuration is missing or malformed."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated runtime settings."""

    environment: str


def load_settings(
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Load and validate settings from environment variables.

    No configuration values are printed or logged here.
    This keeps future secret values out of error messages and output.
    """

    source = os.environ if environ is None else environ

    environment = source.get(ENVIRONMENT_VARIABLE)

    if environment is None or not environment.strip():
        raise ConfigurationError(
            f"Required configuration '{ENVIRONMENT_VARIABLE}' is missing."
        )

    environment = environment.strip().lower()

    if environment not in ALLOWED_ENVIRONMENTS:
        allowed = ", ".join(sorted(ALLOWED_ENVIRONMENTS))

        raise ConfigurationError(
            f"Configuration '{ENVIRONMENT_VARIABLE}' must be one of: "
            f"{allowed}."
        )

    return Settings(environment=environment)
