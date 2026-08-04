"""Side-effect-free configuration for future Google Cloud adapter bindings."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class GcpAdapterSettings(BaseModel):
    """Validated identifiers required by provider-specific adapter factories."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str = Field(pattern=r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
    region: str = Field(pattern=r"^[a-z]+-[a-z]+[0-9]+$")
    firestore_database: str = Field(default="(default)", min_length=1, max_length=63)
    task_queue: str = Field(pattern=r"^[a-z][a-z0-9-]{0,98}[a-z0-9]$")
    artifact_bucket: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{1,61}[a-z0-9]$")
    identity_audience: str = Field(min_length=6, max_length=253)
    worker_audience: HttpUrl


class CloudAdapterBinding(BaseModel):
    """One application port and its intended managed implementation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    port: str
    service: str
    resource: str
    activation: Literal["external_activation_required"] = "external_activation_required"


class GcpAdapterManifest(BaseModel):
    """Reviewable future binding map that performs no network or SDK calls."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str
    region: str
    bindings: tuple[CloudAdapterBinding, ...]


def build_gcp_adapter_manifest(settings: GcpAdapterSettings) -> GcpAdapterManifest:
    """Map application boundaries to fully scoped Google Cloud resources."""

    project = settings.project_id
    region = settings.region
    bindings = (
        CloudAdapterBinding(
            port="IdentityProvider",
            service="Identity Platform / OIDC",
            resource=settings.identity_audience,
        ),
        CloudAdapterBinding(
            port="WorkflowRepository",
            service="Firestore",
            resource=f"projects/{project}/databases/{settings.firestore_database}",
        ),
        CloudAdapterBinding(
            port="TaskQueue",
            service="Cloud Tasks",
            resource=f"projects/{project}/locations/{region}/queues/{settings.task_queue}",
        ),
        CloudAdapterBinding(
            port="TaskHandler",
            service="Cloud Run IAM + OIDC",
            resource=str(settings.worker_audience),
        ),
        CloudAdapterBinding(
            port="AuditSink",
            service="Cloud Logging",
            resource=f"projects/{project}/logs/agentic-audit",
        ),
        CloudAdapterBinding(
            port="OperationalTelemetry",
            service="Cloud Monitoring / OpenTelemetry",
            resource=f"projects/{project}",
        ),
        CloudAdapterBinding(
            port="RateLimiter",
            service="Cloud Armor / distributed adapter",
            resource=f"projects/{project}/global/securityPolicies/agentic-api",
        ),
        CloudAdapterBinding(
            port="ArtifactStore",
            service="Cloud Storage",
            resource=f"gs://{settings.artifact_bucket}",
        ),
        CloudAdapterBinding(
            port="SecretProvider",
            service="Secret Manager",
            resource=f"projects/{project}/secrets/*",
        ),
    )
    return GcpAdapterManifest(project_id=project, region=region, bindings=bindings)
