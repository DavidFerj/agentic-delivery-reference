# Phase 7 Acceptance Criteria

- **AC7-001** — Google Cloud infrastructure is declared as code and creates no resources unless an explicit activation variable is set.
- **AC7-002** — Development and staging use separate variable and state-prefix examples; production activation is not included in this phase.
- **AC7-003** — Web, API, worker, evaluator, task invocation, and deployment use distinct service identities with scoped roles.
- **AC7-004** — The target topology declares public web and API Cloud Run services, a private worker, and an evaluator Cloud Run Job.
- **AC7-005** — Firestore, Cloud Tasks, Cloud Storage, Secret Manager, Artifact Registry, logging, monitoring, and a budget guard are represented declaratively.
- **AC7-006** — A typed Python manifest maps application-owned ports to intended GCP adapters without importing provider SDKs into domain or application modules.
- **AC7-007** — CI validates application quality, Terraform formatting/validation, deployment policy, and repository evidence without cloud credentials.
- **AC7-008** — CD is manual-only, uses GitHub OIDC/Workload Identity Federation, and contains no long-lived service-account key path.
- **AC7-009** — Local planning and deployment scripts default to preview and require explicit, environment-bound acknowledgements before any mutation.
- **AC7-010** — Terraform validation can run with a local backend and placeholder values without refreshing or creating cloud resources.
- **AC7-011** — State, plans, credentials, generated variable files, and secrets remain excluded from version control.
- **AC7-012** — Phase 0–6 behavior remains unchanged and all quality, security, evaluation, native smoke, and containerized smoke gates pass.
- **AC7-013** — Evidence clearly distinguishes structurally verified deployment readiness from an unperformed cloud deployment.

## Evidence

- `evaluations/reports/phase-7-gcp-deployment-readiness.json`
- `scripts/infra/validate-gcp-readiness.ps1`
- `scripts/demo/phase-7-smoke.ps1`
