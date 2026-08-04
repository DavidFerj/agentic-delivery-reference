# ADR-0008: Executable data-protection control plane

## Status

Accepted for Phase 3.5.

## Decision

Introduce a provider-neutral Python package between request adaptation and every material processing boundary. It classifies declared and narrowly detected data, evaluates a versioned baseline policy, emits obligations, and permits or denies execution before persistence, model routing, retrieval, or tool calls.

The API uses `enforce` by default. `observe` and `warn` exist only to measure legacy impact: they retain a deny outcome and audit trail but do not block. Industry overlays are declarative templates with `enabled: false` and `requires_legal_review`; the application rejects them until separately approved and implemented.

## Consequences

- Data purpose, category, provider, jurisdiction, policy version, decision, and obligations travel with the workflow.
- Provider adapters can later consume the same decision contract without coupling policy code to OpenAI, n8n, Vapi, or MCP.
- The deterministic classifier is a reference control, not production DLP or a legal applicability determination.
- Durable audit evidence, consent management, deletion execution, KMS, and sector-specific enforcement remain later platform work.
