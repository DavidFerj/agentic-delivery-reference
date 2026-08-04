# ADR-0009: Bound approval to a local asynchronous task boundary

## Status

Accepted for Phase 4.

## Decision

Planning produces a typed ticket proposal and pauses before any side effect. The proposal digest covers the action and canonical arguments; its schema hash and expiry are stored with it. A reviewer or administrator who is not the workflow owner may approve or reject exactly that proposal.

Approval enqueues one typed execution task behind an application-owned port. The local adapter is process-memory and deliberately requires a second operator call to process queued work, making the asynchronous boundary observable and deterministic. The simulated ticket executor is idempotent by task key. A later Cloud Tasks or n8n adapter must implement the same contracts and delivery semantics.

Data-protection policy is evaluated again immediately before tool execution. The approval is consumed only after the stored execution result completes the workflow.

## Consequences

- Model output has no direct execution authority.
- Self-approval, altered proposals, expired decisions, unauthorized processing, and duplicate side effects fail safely.
- The local queue, repository, approval, and audit state disappear on API restart; durable transactional state remains a later phase.
- Phase 4 proves asynchronous application semantics, not Cloud Tasks, n8n, or a production ticket provider.
