# ADR-0011: Local security and operational hardening

## Status

Accepted for Phase 6.

## Decision

The API composition root installs an allowlist-only operational middleware. It establishes one correlation identifier, measures request duration, records a route-template observation after response handling, returns defensive HTTP headers, and never records headers, query values, request bodies, prompts, or response bodies.

The local audit adapter creates immutable structured events with an event identifier and UTC timestamp. Its public operations view is administrator-only and contains no payload field. A reusable sanitizer recursively redacts configured field names and common credential-shaped strings; tests prove the sanitizer independently because payloads are intentionally absent from request telemetry.

Liveness remains a process signal. A separate readiness endpoint reports only named local component checks. Operator and administrator roles may read aggregate request metrics, while only administrators may read sanitized audit events. Mutable endpoints use a configurable in-memory fixed-window limiter scoped to the verified principal.

These adapters demonstrate contracts and control placement. Cloud Logging, OpenTelemetry collectors, managed metrics, SIEM export, managed rate limiting, and durable audit storage remain later cloud adapters.

## Consequences

- Operational diagnosis can follow one correlation identifier without access to user content.
- Security headers, rate limits, audit evidence, and role restrictions are executable and testable locally.
- Process restart clears telemetry, audit, and rate-limit state.
- The in-process limiter cannot coordinate multiple replicas and must be replaced by an appropriate distributed or edge control before scaled production use.
