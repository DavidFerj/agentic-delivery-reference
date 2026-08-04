# ADR-0010: Local RAG, guardrails, and deterministic evaluation gates

## Status

Accepted for Phase 5.

## Decision

The runtime depends on a retrieval port and ships with a versioned, synthetic local corpus. Retrieval is deterministic and lexical so the mandatory test and demo profiles remain reproducible and require no network, embedding service, vector database, or GPU. Every selected passage carries provenance and a content hash.

Retrieved text is data, never executable instruction. A guardrail scans user input before classification, quarantines suspicious retrieved passages before context construction, and scans the structured proposal before it can become a tool proposal. The initial patterns are intentionally narrow and versioned; they demonstrate an enforceable boundary rather than claiming comprehensive content-security detection.

A deterministic evaluation gate runs after proposal generation and before `awaiting_approval`. It requires valid structure, at least one grounded citation, matching citation hashes, and a safe output. The application creates a tool proposal only for a passing result. Recognized prompt injection and failed evaluation are mapped to safe API problems and security-relevant audit outcomes.

The evaluator job executes a versioned golden set with normal and adversarial cases. Its local release threshold is 100%; adding a real embedding retriever or LLM-as-judge later requires a separate optional adapter and baseline.

## Consequences

- The Phase 5 slice has meaningful RAG and safety behavior without external accounts.
- Retrieval, guardrails, and evaluation are replaceable at explicit ports or cohesive runtime boundaries.
- Lexical relevance and pattern detection have known recall limitations and must not be marketed as production DLP, a complete jailbreak defense, or semantic quality judgment.
- No failed evaluation or blocked input can reach human approval or tool execution.
