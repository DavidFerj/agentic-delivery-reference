"""Validate the plan-only Google Cloud delivery contract without provider access."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
TERRAFORM_ROOT = ROOT / "infra" / "terraform" / "gcp-platform"


def _require_text(path: Path, required: tuple[str, ...], errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"Missing required file: {path.relative_to(ROOT)}")
        return
    content = path.read_text(encoding="utf-8")
    for marker in required:
        if marker not in content:
            errors.append(f"Missing '{marker}' in {path.relative_to(ROOT)}")


def validate_terraform(errors: list[str]) -> None:
    """Verify provider, activation, platform, identity, and managed-service declarations."""

    _require_text(
        TERRAFORM_ROOT / "variables.tf",
        (
            'variable "allow_resource_creation"',
            "default     = false",
            'variable "runtime_adapters_ready"',
            'check "activation_is_deliberate"',
            '["development", "staging"]',
        ),
        errors,
    )
    _require_text(
        TERRAFORM_ROOT / "backend.gcs.tf.example",
        ('backend "gcs"',),
        errors,
    )
    _require_text(
        TERRAFORM_ROOT / "main.tf",
        (
            'resource "google_cloud_run_v2_service" "web"',
            'resource "google_cloud_run_v2_service" "api"',
            'resource "google_cloud_run_v2_service" "worker"',
            'resource "google_cloud_run_v2_job" "evaluator"',
            'resource "google_firestore_database" "operational"',
            'resource "google_cloud_tasks_queue" "execution"',
            'resource "google_storage_bucket" "artifacts"',
            'resource "google_secret_manager_secret" "provider_credentials"',
            'resource "google_iam_workload_identity_pool_provider" "github"',
            'resource "google_logging_metric" "api_errors"',
            'resource "google_monitoring_dashboard" "operations"',
            'resource "google_billing_budget" "environment"',
            'attribute_condition                = "assertion.repository ==',
            "local.active ?",
        ),
        errors,
    )

    for environment in ("development", "staging"):
        tfvars = ROOT / "infra" / "terraform" / "environments" / f"{environment}.tfvars.example"
        backend = (
            ROOT / "infra" / "terraform" / "environments" / f"{environment}.backend.hcl.example"
        )
        _require_text(
            tfvars,
            (
                f'environment            = "{environment}"',
                "allow_resource_creation = false",
                "runtime_adapters_ready  = false",
            ),
            errors,
        )
        _require_text(backend, (f'prefix = "agentic-delivery-reference/{environment}"',), errors)

    if (ROOT / "infra" / "terraform" / "environments" / "production.tfvars.example").exists():
        errors.append("Phase 7 must not include a production activation file")


def validate_delivery_workflow(errors: list[str]) -> None:
    """Require manual, keyless, confirmation-bound cloud delivery."""

    path = ROOT / ".github" / "workflows" / "deploy-gcp.yml"
    if not path.is_file():
        errors.append("Missing manual Google Cloud deployment workflow")
        return
    content = path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(content)
    triggers = workflow.get("on", workflow.get(True, {}))
    if set(triggers) != {"workflow_dispatch"}:
        errors.append("GCP deployment workflow must be manual-only")
    required = (
        "id-token: write",
        "google-github-actions/auth@",
        "workload_identity_provider",
        "service_account",
        "DEPLOY-",
        "terraform apply",
        "-refresh=false",
    )
    for marker in required:
        if marker not in content:
            errors.append(f"Missing '{marker}' in {path.relative_to(ROOT)}")
    forbidden = ("credentials_json", "service_account_key", "pull_request:", "push:")
    for marker in forbidden:
        if marker in content:
            errors.append(f"Forbidden '{marker}' in {path.relative_to(ROOT)}")


def validate_mutation_gates(errors: list[str]) -> None:
    """Keep apply capability isolated behind explicit local and CI acknowledgements."""

    apply_locations: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(
            part in {".git", ".terraform", ".venv"} for part in path.parts
        ):
            continue
        if path.suffix not in {".ps1", ".yml", ".yaml"}:
            continue
        content = path.read_text(encoding="utf-8")
        if "terraform apply" in content or re.search(r"terraform\s+[^\r\n]*\bapply\b", content):
            apply_locations.append(path.relative_to(ROOT))
    allowed = {
        Path(".github/workflows/deploy-gcp.yml"),
        Path("scripts/deploy/deploy-gcp.ps1"),
    }
    if set(apply_locations) != allowed:
        errors.append(f"Terraform apply locations differ from the allowlist: {apply_locations}")

    _require_text(
        ROOT / "scripts" / "deploy" / "deploy-gcp.ps1",
        (
            "ADR_ALLOW_GCP_MUTATION",
            '"DEPLOY-$Environment"',
            'if ($Environment -eq "production")',
            "runtime_adapters_ready=true",
            "allow_resource_creation=true",
        ),
        errors,
    )


def main() -> int:
    """Return a non-zero exit code when the deployment contract is unsafe or incomplete."""

    errors: list[str] = []
    validate_terraform(errors)
    validate_delivery_workflow(errors)
    validate_mutation_gates(errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Google Cloud plan-only readiness validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
