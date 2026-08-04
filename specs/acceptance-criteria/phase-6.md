# Phase 6 Acceptance Criteria

## Outcome

The local profile exposes production-shaped security and operational boundaries without exporting sensitive payloads or requiring a remote observability, identity, or security service.

## Criteria

- **AC6-001** — Every API response carries a validated or generated correlation identifier, and the same identifier is used by workflow audit and request telemetry.
- **AC6-002** — Request telemetry records only allowlisted operational fields: method, route template, status, duration, correlation identifier, and timestamp.
- **AC6-003** — Audit events contain event identifier, timestamp, actor, action, resource, decision, outcome, and correlation identifier without request or credential payloads.
- **AC6-004** — Configured sensitive field names and bearer, API-key, email, and credential-shaped values are redacted by a reusable local sanitizer.
- **AC6-005** — Liveness and readiness are separate endpoints; readiness reports component checks without exposing configuration or secrets.
- **AC6-006** — Mutable protected endpoints enforce a configurable, per-principal fixed-window limit and return a safe `429` response when exhausted.
- **AC6-007** — API responses include anti-sniffing, frame, referrer, content-security, and no-store headers.
- **AC6-008** — Operational metrics are available only to operator or administrator roles; sanitized audit evidence is administrator-only.
- **AC6-009** — Operational endpoints do not expose raw prompts, authorization headers, idempotency keys, or data payloads.
- **AC6-010** — A deterministic red-team suite covers anonymous access, broken role access, invalid metadata, rate abuse, prompt injection, sensitive-value redaction, and oversized input.
- **AC6-011** — CI runs the red-team suite, repository secret validation, dependency audits, evaluation gate, tests, types, lint, contracts, and builds.
- **AC6-012** — Python and web changed business logic achieve 100% statement and branch coverage; native and containerized Phase 6 smoke tests pass.
- **AC6-013** — The capability registry links source, tests, demo, documentation, and machine-readable evidence.
- **AC6-014** — Local telemetry, audit, and rate-limit state remain explicitly non-durable and are not presented as managed production services.

## Exit evidence

- `evaluations/reports/phase-6-security-operational-hardening.json`
- `evaluations/reports/red-team-deterministic-v1.json`
- `scripts/security/run-red-team.ps1`
- `scripts/demo/phase-6-smoke.ps1`
