# Phase 5 Acceptance Criteria

## Outcome

The deterministic local workflow retrieves versioned knowledge, treats every retrieved document as untrusted content, blocks prompt-injection attempts, and creates an approvable action only after a reproducible evaluation gate passes.

## Criteria

- **AC5-001** — Retrieval uses an application-owned port and a versioned local corpus; no network or paid provider is required.
- **AC5-002** — Each selected passage records document identity, version, section, relevance score, and a SHA-256 content hash.
- **AC5-003** — The proposal visibly incorporates guidance from at least one cited passage.
- **AC5-004** — User input containing a recognized instruction-override pattern is rejected before provider invocation or tool proposal creation.
- **AC5-005** — Retrieved passages containing instruction-override patterns are quarantined and cannot influence the proposal.
- **AC5-006** — A deterministic gate checks structured output, grounding, citation integrity, and output safety before approval becomes available.
- **AC5-007** — A failed gate stops planning safely, records an audit outcome, and creates no action proposal.
- **AC5-008** — A versioned golden set contains normal, boundary, and adversarial cases and passes at a 100% deterministic threshold.
- **AC5-009** — The web console shows corpus version, selected and quarantined evidence, guardrail outcome, and evaluation score.
- **AC5-010** — Python and web changed business logic achieve 100% statement and branch coverage; native and containerized Phase 5 smoke tests pass.
- **AC5-011** — The capability registry links source, tests, demo, documentation, and machine-readable evidence.
- **AC5-012** — External LLMs, embeddings, vector databases, LLM-as-judge services, and live integrations remain disabled and are not presented as operational.

## Exit evidence

- `evaluations/reports/phase-5-rag-guardrails-evaluation.json`
- `evaluations/reports/golden-set-deterministic-v1.json`
- `scripts/demo/phase-5-smoke.ps1`
- `scripts/evaluation/run-golden-set.ps1`
