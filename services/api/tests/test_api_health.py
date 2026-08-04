"""API liveness and documentation behavior."""

from fastapi.testclient import TestClient

from agentic_api.config import ApiSettings
from agentic_api.main import create_app


def test_health_reports_service_and_environment() -> None:
    with TestClient(create_app(ApiSettings(environment="development"))) as client:
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": "api",
            "environment": "development",
        }


def test_documentation_is_available_outside_production() -> None:
    app = create_app(ApiSettings(environment="local"))

    assert app.docs_url == "/docs"


def test_production_profile_fails_closed_before_app_creation() -> None:
    try:
        create_app(ApiSettings(environment="production"))
    except ValueError as error:
        assert str(error) == "Local authentication is forbidden in production"
    else:
        raise AssertionError("Production must not start with local authentication")
