"""Configuration tests."""

import pytest
from agentic_governance.models import EnforcementMode
from pydantic import ValidationError

from agentic_api.config import ApiSettings, get_settings


def test_default_settings_are_safe_for_local_use(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ADR_ENVIRONMENT", raising=False)
    monkeypatch.delenv("ADR_LOG_LEVEL", raising=False)
    monkeypatch.delenv("ADR_GOVERNANCE_MODE", raising=False)

    settings = ApiSettings()

    assert settings.environment == "local"
    assert settings.log_level == "INFO"
    assert settings.auth_mode == "local"
    assert settings.web_origin == "http://localhost:3000"
    assert settings.governance_mode == EnforcementMode.ENFORCE
    assert settings.rate_limit_requests == 100
    assert settings.rate_limit_window_seconds == 60


def test_settings_load_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADR_ENVIRONMENT", "staging")
    monkeypatch.setenv("ADR_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("ADR_GOVERNANCE_MODE", "warn")
    monkeypatch.setenv("ADR_RATE_LIMIT_REQUESTS", "25")
    monkeypatch.setenv("ADR_RATE_LIMIT_WINDOW_SECONDS", "30")

    settings = ApiSettings()

    assert settings.environment == "staging"
    assert settings.log_level == "WARNING"
    assert settings.governance_mode == EnforcementMode.WARN
    assert settings.rate_limit_requests == 25
    assert settings.rate_limit_window_seconds == 30


def test_invalid_environment_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADR_ENVIRONMENT", "personal")

    with pytest.raises(ValidationError):
        ApiSettings()


def test_cached_settings_returns_same_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ADR_ENVIRONMENT", "development")

    first = get_settings()
    second = get_settings()

    assert first is second
    assert first.environment == "development"
    get_settings.cache_clear()


def test_local_authentication_is_rejected_in_production() -> None:
    settings = ApiSettings(environment="production")

    with pytest.raises(ValueError, match="forbidden"):
        settings.assert_safe_profile()


def test_local_authentication_is_allowed_outside_production() -> None:
    ApiSettings(environment="development").assert_safe_profile()
