# Google Cloud plan-only runbook

## Purpose

Phase 7 prepares a reviewable Google Cloud deployment without authenticating, creating a project, enabling an API, linking billing, or applying Terraform. Local runtime behavior remains unchanged.

## Safe local validation

Run the static contract and smoke tests without Terraform:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/infra/validate-gcp-readiness.ps1 -SkipTerraform
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-7-smoke.ps1
```

When Terraform is installed, validate provider schemas with a local backend. This downloads the provider but performs no refresh or apply:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/infra/validate-gcp-readiness.ps1
```

Preview the inert plan command. Without `-ExecutePlan`, the script prints the command and exits:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/deploy/plan-gcp.ps1 `
  -Environment development `
  -ProjectId agentic-dev-12345
```

## Target resources

- Artifact Registry for immutable web and Python runtime images
- Public Cloud Run web and API services
- Private Cloud Run worker invoked through Cloud Tasks and OIDC
- Cloud Run Job for deterministic evaluation
- Firestore, Cloud Storage, and Secret Manager
- Cloud Logging metric, Cloud Monitoring dashboard, and billing budget thresholds
- Separate runtime and deployment service accounts
- GitHub OIDC Workload Identity Federation with a repository-bound condition

All managed resources use `allow_resource_creation`. Its default is `false`, producing no managed resources. Activation also requires `runtime_adapters_ready`, a real project number, a non-placeholder GitHub repository, explicit scripts/workflow confirmation, an existing project, billing review, and an approved remote-state bootstrap.

## Activation boundary

Do not run `scripts/deploy/deploy-gcp.ps1` or the manual GitHub deployment workflow until all of the following are authorized and verified:

1. Separate development or staging project and billing account exist.
2. Terraform state bucket and access policy are approved.
3. GitHub environments require appropriate reviewers.
4. Workload Identity Federation is bootstrapped without a service-account key.
5. Provider SDK adapters pass emulator/integration tests.
6. Immutable container digests and rollback revisions are available.
7. IAM, data residency, retention, cost, and incident controls are reviewed.

Production is rejected by the Phase 7 local deployment script and Terraform environment validation.

## Rollback design

Cloud Run retains revisions so traffic can be returned to a previous immutable digest. Terraform changes must be reviewed from a saved plan; state versioning protects prior state snapshots. Firestore and artifact lifecycle changes require a separate data recovery plan and are not automated in Phase 7.
