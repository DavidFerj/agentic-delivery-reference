# Test Plan

## Purpose

Validate the product requirements, contracts, failure behavior, security boundaries, and operational evidence without relying on paid external services.

## Test levels

| Level | Scope |
| --- | --- |
| Unit | Domain rules, policies, state transitions, cost calculations, and evaluators |
| Component | API routes, LangGraph nodes, adapters, UI components, and authorization guards |
| Contract | OpenAPI, event schemas, tool schemas, and every simulated/real adapter pair |
| Integration | Firestore emulator, Storage emulator or local adapter, queue adapter, and checkpoint persistence |
| End-to-end | Request through approval, side effect, evaluation, and evidence display |
| Security | Access control, injection, secret leakage, replay, SSRF, and unsafe tool use |
| Resilience | Retry, timeout, duplicate delivery, stale state version, and interrupted execution |
| Evaluation | Golden-set quality, grounding, schema validity, safety, and drift |

## Acceptance traceability

| Criteria | Planned validation |
| --- | --- |
| AC-001–AC-004 | API integration and end-to-end local tests |
| AC-005–AC-008 | Approval policy, state-machine, concurrency, and idempotency tests |
| AC-009–AC-012 | Authentication, authorization, adversarial, and log-redaction tests |
| AC-013 | End-to-end UI test and evidence-schema assertions |
| AC-014–AC-016 | Golden-set runner, failing-gate fixture, capability-map validator |
| AC-017 | Clean-environment setup smoke test |
| AC-018–AC-019 | Infrastructure validation, development deployment smoke test, and rollback rehearsal |
| AC-020 | Disabled-adapter and safe-failure contract tests |
| AC0-001–AC0-008 | Phase 0 document, schema, link, and traceability validation |

## Mandatory boundary cases

- Empty, too short, too long, malformed Unicode, and unsupported locale input
- Missing, expired, malformed, wrong-audience, and revoked identity token behavior
- Cross-user resource access and self-approval attempts
- Stale `state_version` and simultaneous approval decisions
- Replayed approval and idempotency keys
- Prompt injection in both the user request and retrieved content
- Tool arguments containing unexpected properties or unsafe URLs
- Provider timeout, rate limit, invalid structured output, and permanent failure
- Worker duplicate delivery and failure after side effect but before acknowledgment
- Missing citation, irrelevant citation, and citation hash mismatch
- Sensitive values in request fields, provider errors, and headers

## Coverage policy

New or modified production business logic targets 100% statement and branch coverage where the tooling supports meaningful measurement. Exclusions require an explicit narrow justification. Coverage does not replace behavioral assertions.

## Determinism policy

The required CI suite uses deterministic providers, fixed clocks, stable identifiers, synthetic data, and controlled random seeds. Network calls are prohibited in unit tests. Optional live-provider suites are separate, manually authorized, and never required for local success.

## Quality gates

The main branch protection workflow will require:

- Formatting and linting
- Static type checking
- Unit, component, integration, and contract tests
- Required coverage thresholds
- Dependency and secret scanning
- Container and infrastructure validation
- Deterministic golden-set thresholds
- Successful production builds for all deployables

## Environments

| Environment | Test purpose | Data |
| --- | --- | --- |
| Local | Full deterministic development suite | Synthetic |
| Development | Managed-service integration and deployment smoke | Synthetic |
| Staging | UAT, release, security, and rollback rehearsal | Synthetic or approved sanitized |
| Production | Out of initial scope | No test data assumption |

## Entry and exit

A phase begins after its prerequisite specifications and contracts are stable. It exits only when its mapped acceptance criteria pass, evidence is recorded, and no blocking security finding remains.
