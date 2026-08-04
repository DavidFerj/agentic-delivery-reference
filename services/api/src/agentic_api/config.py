"""Validated runtime configuration for the API."""

from functools import lru_cache
from typing import Literal

from agentic_governance.models import EnforcementMode
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """Configuration loaded from ADR-prefixed environment variables."""

    environment: Literal["local", "development", "staging", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    auth_mode: Literal["local"] = "local"
    web_origin: str = "http://localhost:3000"
    governance_mode: EnforcementMode = EnforcementMode.ENFORCE
    rate_limit_requests: int = Field(default=100, ge=1, le=10_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3_600)

    model_config = SettingsConfigDict(env_prefix="ADR_", extra="ignore")

    def assert_safe_profile(self) -> None:
        """Prevent development credentials from being enabled in production."""

        if self.environment == "production" and self.auth_mode == "local":
            raise ValueError("Local authentication is forbidden in production")


@lru_cache
def get_settings() -> ApiSettings:
    """Return one immutable settings snapshot per process."""

    return ApiSettings()
