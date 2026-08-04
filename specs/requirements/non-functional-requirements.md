# Non-Functional Requirements

## Security

- **NFR-001:** Protected endpoints shall deny access by default.
- **NFR-002:** Secrets and credentials shall never be committed, logged, returned in errors, or included in fixtures.
- **NFR-003:** Service identities shall receive only permissions required by their deployable.
- **NFR-004:** External input, retrieved content, model output, and tool arguments shall be treated as untrusted.
- **NFR-005:** Sensitive operations shall require server-side authorization and cannot rely on client assertions.
- **NFR-006:** Logs and traces shall redact configured sensitive fields.
- **NFR-007:** The system shall mitigate prompt injection by separating instructions from untrusted content and enforcing tool policy outside the model.

## Reliability

- **NFR-008:** Workflow transitions and approval consumption shall use concurrency-safe updates.
- **NFR-009:** Transient retries shall be bounded and use backoff.
- **NFR-010:** Permanent failures shall terminate or pause safely with an actionable recorded reason.
- **NFR-011:** Side effects shall use idempotency keys and be safe under at-least-once delivery.
- **NFR-012:** No persistent state shall depend on a container's local filesystem.

## Performance and scalability

- **NFR-013:** API requests not performing agent execution should target a p95 latency below 500 ms in the development profile, excluding cold starts.
- **NFR-014:** Long-running work shall execute asynchronously outside interactive HTTP request lifetimes.
- **NFR-015:** Web, API, worker, and evaluator shall be independently deployable and scalable.
- **NFR-016:** Concurrency and maximum instance settings shall protect downstream services and budgets.

## Observability and auditability

- **NFR-017:** All logs, traces, metrics, and audit events for a workflow shall share a correlation identifier.
- **NFR-018:** Audit records shall include actor, action, resource, timestamp, decision, and outcome.
- **NFR-019:** Operational diagnostics shall not require access to sensitive prompt or payload content.
- **NFR-020:** Health and readiness signals shall distinguish process health from dependency readiness.

## Maintainability and portability

- **NFR-021:** Domain and application code shall not import provider SDKs directly.
- **NFR-022:** API and event contracts shall be versioned and backward-compatible within a major version.
- **NFR-023:** New and modified business logic shall target 100% statement and branch coverage where meaningful.
- **NFR-024:** Local and cloud profiles shall share contracts and behavior even when adapters differ.
- **NFR-025:** Dependencies shall be pinned through lock files and added only when they provide a concrete benefit.

## Accessibility and usability

- **NFR-026:** The web console shall use semantic HTML and support keyboard navigation.
- **NFR-027:** Loading, empty, success, disabled, and error states shall be explicit.
- **NFR-028:** Recoverable errors shall preserve user-entered request data.

## Cost

- **NFR-029:** Local mode shall operate without paid APIs.
- **NFR-030:** Each model execution shall record an estimated cost even when the estimate is zero for a simulator.
- **NFR-031:** Cloud resources shall have documented scaling bounds and budget implications.
