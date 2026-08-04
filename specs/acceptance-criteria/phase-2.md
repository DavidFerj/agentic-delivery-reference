# Phase 2 Acceptance Criteria

## Authenticated vertical slice

- **AC2-001:** An anonymous or invalid bearer credential is denied on every protected endpoint with safe RFC 7807 problem details.
- **AC2-002:** Each documented local identity resolves to exactly one requester, reviewer, operator, or administrator role.
- **AC2-003:** A requester or administrator can submit a schema-valid request and receives a `received` workflow with an owner, initial transition, state version, and correlation identifier.
- **AC2-004:** Request text and locale are normalized before storage, and invalid input cannot create a workflow.
- **AC2-005:** Reusing an idempotency key with the same owner and payload returns the original workflow; changing the payload returns a conflict.
- **AC2-006:** Owners can read their workflows, operators and administrators can inspect any workflow, and other callers receive a non-enumerating not-found response.
- **AC2-007:** Allowed and denied workflow actions produce sanitized local audit events.
- **AC2-008:** The web console preserves an actionable success or error state while calling the protected API.
- **AC2-009:** The native smoke test proves the web/API request journey without a paid or external service.
- **AC2-010:** Production startup fails closed while the local identity adapter is selected.

## Deliberate boundaries

- Persistence is process-local in this phase; the repository port is the replacement boundary for Firestore.
- Local bearer values are public development fixtures and are forbidden in production.
- Workflow execution remains at `received`; LangGraph, knowledge retrieval, approval, tools, and external providers begin in later phases.
