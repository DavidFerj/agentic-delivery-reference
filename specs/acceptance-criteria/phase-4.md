# Phase 4 Acceptance Criteria

**AC4-001** Planning creates an immutable `create_delivery_ticket` proposal and pauses the workflow in `awaiting_approval` without executing a side effect.

**AC4-002** The proposal carries an expiry, schema hash, and canonical digest that bind any decision to the exact action and arguments.

**AC4-003** Only a reviewer or administrator may decide a proposal, and no principal may approve their own request.

**AC4-004** Approval and rejection are one-time, idempotent decisions; a conflicting replay or stale state fails safely.

**AC4-005** Rejection and expiration create no execution task or simulated ticket and remain visible and audited.

**AC4-006** Approval enqueues one local execution task and returns before that task is processed.

**AC4-007** Only an operator or administrator may process queued work, and data-governance policy is evaluated again before tool execution.

**AC4-008** Duplicate task delivery returns the original simulated ticket and never creates a second side effect.

**AC4-009** A successful task transitions through `executing`, `evaluating`, and `completed`, consumes the approval, and exposes execution evidence.

**AC4-010** API, web console, audit events, OpenAPI, tests, and a local demo expose the complete pause, decision, and execution journey without external services.
