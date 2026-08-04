# ADR-0012: Plan-only Google Cloud deployment readiness

## Status

Accepted for Phase 7.

## Decision

Phase 7 prepares Google Cloud delivery without provisioning a project or billable resource. Terraform declares the target platform behind `allow_resource_creation = false`; development and staging examples preserve separate state prefixes and variables. A second `runtime_adapters_ready` gate prevents infrastructure activation from being presented as application readiness.

The target topology follows ADR-0003: public Cloud Run web and API services, a private worker, an evaluator Cloud Run Job, Firestore, Cloud Tasks with OIDC delivery, Cloud Storage, Secret Manager, Artifact Registry, managed logging and monitoring, and a budget notification threshold. Every deployable and the deployment pipeline has a distinct service account. CI/CD authentication is designed for GitHub OIDC and Workload Identity Federation; service-account keys are forbidden.

Application modules continue to own their ports. A typed, side-effect-free Python manifest validates deployment identifiers and documents the intended GCP binding for identity, persistence, task dispatch, audit, telemetry, rate limiting, secrets, and artifacts. It does not claim that provider SDK adapters or cloud behavior have been exercised. Local adapters remain the only active runtime profile.

CI may initialize providers and validate Terraform using placeholder identifiers, the default disposable local backend, disabled resource activation, and no refresh. The GCS backend declaration is an inert template copied only inside an authorized deployment. The manual deployment workflow and PowerShell scripts require explicit environment-bound acknowledgements before mutation. Production is deliberately rejected.

## Consequences

- Infrastructure and delivery contracts can be reviewed and evolved without a Google Cloud account or cost.
- An accidental default `terraform apply` has an empty resource graph.
- Cloud adapter activation, remote state bootstrap, workload federation creation, project creation, billing linkage, and real deployment remain authorized future operations.
- Structural validation is evidence of deployment readiness, not evidence of cloud operation, certification, availability, or cost.
