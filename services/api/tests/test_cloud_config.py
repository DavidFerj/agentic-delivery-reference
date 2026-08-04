"""Tests for side-effect-free Google Cloud deployment bindings."""

import pytest
from pydantic import HttpUrl, ValidationError

from agentic_api.cloud_config import GcpAdapterSettings, build_gcp_adapter_manifest


def _settings() -> GcpAdapterSettings:
    return GcpAdapterSettings(
        project_id="agentic-dev-12345",
        region="us-central1",
        task_queue="agentic-execution",
        artifact_bucket="agentic-dev-12345-artifacts",
        identity_audience="agentic-dev-12345",
        worker_audience=HttpUrl("https://agentic-worker-abc-uc.a.run.app"),
    )


def test_manifest_maps_every_external_boundary_without_side_effects() -> None:
    manifest = build_gcp_adapter_manifest(_settings())

    assert manifest.project_id == "agentic-dev-12345"
    assert manifest.region == "us-central1"
    assert {binding.port for binding in manifest.bindings} == {
        "ArtifactStore",
        "AuditSink",
        "IdentityProvider",
        "OperationalTelemetry",
        "RateLimiter",
        "SecretProvider",
        "TaskHandler",
        "TaskQueue",
        "WorkflowRepository",
    }
    assert all(
        binding.activation == "external_activation_required" for binding in manifest.bindings
    )
    assert manifest.bindings[1].resource.endswith("/databases/(default)")
    assert manifest.bindings[2].resource.endswith("/queues/agentic-execution")
    assert manifest.bindings[7].resource == "gs://agentic-dev-12345-artifacts"


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("project_id", "INVALID"),
        ("region", "local"),
        ("task_queue", "Invalid_queue"),
        ("artifact_bucket", "UPPERCASE"),
        ("worker_audience", "not-a-url"),
    ),
)
def test_invalid_cloud_identifiers_are_rejected(field: str, value: str) -> None:
    values = _settings().model_dump(mode="json")
    values[field] = value

    with pytest.raises(ValidationError):
        GcpAdapterSettings.model_validate(values)


def test_settings_reject_unknown_fields() -> None:
    values = _settings().model_dump(mode="json")
    values["credential"] = "must-not-be-accepted"

    with pytest.raises(ValidationError):
        GcpAdapterSettings.model_validate(values)
