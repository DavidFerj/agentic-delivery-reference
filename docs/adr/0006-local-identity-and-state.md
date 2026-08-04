# ADR-0006: Local Identity and State for Phase 2

- Status: Accepted
- Date: 2026-08-03

## Context

Phase 2 must prove the protected browser-to-API boundary without provisioning Firebase Authentication, Firestore, secrets, or another external service. It must also avoid coupling application behavior to a development simulator.

## Decision

The application core owns identity-provider, workflow-repository, and audit-sink ports. The local profile wires deterministic, documented bearer identities and process-local thread-safe adapters. Backend authorization combines role policy with workflow ownership. The application refuses to start in a production profile while local authentication is enabled.

## Consequences

- The complete authentication, authorization, validation, idempotency, and resource-access journey is reproducible offline.
- Local bearer strings are fixtures, never production credentials.
- State is lost when the API process stops; this is intentional until the persistent adapter phase.
- Firebase/OIDC and Firestore adapters must satisfy these inward-owned contracts and contract tests.
