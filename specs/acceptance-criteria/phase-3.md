# Phase 3 Acceptance Criteria

## Deterministic agent runtime

- **AC3-001:** A received workflow can be planned through an explicit LangGraph `StateGraph` without network access or a paid service.
- **AC3-002:** The graph visits `validated`, `classified`, `context_built`, `knowledge_retrieved`, and `planned` in the specified order.
- **AC3-003:** Rules version `rules-v1` produces stable category and complexity classifications for the same normalized input.
- **AC3-004:** The selected model policy records `deterministic-local`, its version, and the selection reason.
- **AC3-005:** Planning returns a schema-valid proposal, a verifiable local-policy citation, token estimates, and zero estimated model cost.
- **AC3-006:** Graph output cannot mutate workflow state directly; the application validates it and stores every checkpoint through the workflow repository.
- **AC3-007:** Only the workflow owner or an administrator can start planning, and inaccessible workflows remain non-enumerable.
- **AC3-008:** Replaying planning for an already planned workflow returns the stored result without executing a second plan.
- **AC3-009:** A stale repository state version rejects the update instead of overwriting concurrent state.
- **AC3-010:** The console displays classification, model policy, proposal steps, citation, trace identifiers, and zero-cost metrics.
- **AC3-011:** The native smoke test proves authenticated creation, deterministic planning, and retrieval of the stored result.

## Deliberate boundaries

- LangGraph uses an in-memory checkpointer in this phase; durable cross-process checkpointing remains a later persistence adapter.
- `langchain-core` is present as a LangGraph dependency, but no high-level LangChain agent, provider SDK, or external telemetry service is configured.
- The knowledge node retrieves one versioned local policy fixture. General RAG, guardrails, and evaluation gates remain Phase 5.
- Approval, tools, asynchronous execution, and side effects remain disabled until Phase 4.
