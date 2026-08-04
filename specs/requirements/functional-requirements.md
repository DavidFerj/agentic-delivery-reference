# Functional Requirements

## Identity and access

- **FR-001:** The system shall authenticate interactive users before granting access to protected operations.
- **FR-002:** The system shall authorize every protected operation using role and resource ownership.
- **FR-003:** The system shall support requester, reviewer, operator, and administrator roles.

## Requests and execution

- **FR-004:** An authenticated requester shall be able to create a service-delivery request.
- **FR-005:** The API shall validate and normalize incoming requests before persistence or execution.
- **FR-006:** The system shall expose the current execution status and a chronological state history.
- **FR-007:** The runtime shall classify a valid request using a deterministic policy in local mode.
- **FR-008:** The runtime shall select a model-provider policy and record the selection reason.
- **FR-009:** The runtime shall build task context from the request, identity, workflow state, and retrieved knowledge.
- **FR-010:** The runtime shall retrieve relevant knowledge and attach source citations to grounded outputs.
- **FR-011:** The runtime shall produce a structured implementation proposal and complexity estimate.

## State, memory, and resilience

- **FR-012:** The system shall persist workflow state at defined checkpoints.
- **FR-013:** A paused or failed workflow shall resume from the last safe checkpoint.
- **FR-014:** Session memory and durable workflow state shall be represented separately.
- **FR-015:** Retried asynchronous work shall be idempotent.
- **FR-016:** Invalid state transitions shall be rejected and audited.

## Tools and human approval

- **FR-017:** Tool inputs and outputs shall be validated against versioned schemas.
- **FR-018:** Tools shall be classified by risk and permitted roles.
- **FR-019:** A ticket-creation proposal shall require human approval before execution.
- **FR-020:** An authorized reviewer shall be able to approve, edit within policy, or reject a pending proposal.
- **FR-021:** Approval decisions shall be single-use, attributable, time-bound, and audited.
- **FR-022:** Local mode shall execute ticket creation through a deterministic simulated adapter.

## Evaluation and evidence

- **FR-023:** Every execution shall record correlation identifiers, state transitions, model policy, retrieval evidence, tool proposals, approvals, outcomes, and errors.
- **FR-024:** The system shall record latency, estimated tokens, and estimated model cost.
- **FR-025:** A versioned golden set shall cover normal, boundary, failure, and adversarial cases.
- **FR-026:** Deterministic evaluators shall score schema validity, grounding, safety, and task completion.
- **FR-027:** CI shall fail when tests, contracts, security checks, or required evaluation thresholds fail.
- **FR-028:** The console shall display the result and the evidence available to the current user.

## Deployment and integrations

- **FR-029:** The repository shall provide a local profile that does not require paid external services.
- **FR-030:** The repository shall provide an infrastructure-as-code GCP profile and rollback guidance.
- **FR-031:** n8n, Vapi, MCP, ticketing, model, embedding, and notification integrations shall be accessed through explicit ports.
- **FR-032:** Disabled or unavailable integrations shall fail safely without being presented as operational.
- **FR-033:** Integration adapters shall enforce timeouts, bounded retries, error mapping, and audit hooks.
