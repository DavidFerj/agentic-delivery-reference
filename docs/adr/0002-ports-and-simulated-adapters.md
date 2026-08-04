# ADR-0002: Ports and Deterministic Simulated Adapters

- Status: Accepted
- Date: 2026-08-03

## Context

The system must run without paid services now and accept n8n, Vapi, MCP, ticketing, model, embedding, and notification integrations later.

## Decision

Define provider-neutral ports owned by the application. Initial adapters are deterministic simulators. Provider SDKs may appear only inside real adapters. Configuration selects an adapter explicitly; missing configuration never triggers an unsafe fallback.

Every real adapter must pass common contract tests and define authentication, timeout, bounded retry, idempotency, error mapping, telemetry, and audit behavior.

## Consequences

- Core behavior remains testable without network access.
- Simulators are supported runtime components, not mocks presented as external integrations.
- Adding an adapter does not require rewriting use cases.
- Contracts require careful versioning and may not expose every provider-specific feature.
