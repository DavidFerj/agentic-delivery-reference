# Agent Runtime

Phase 3 implements an explicit LangGraph workflow with deterministic local behavior:

1. Validate the normalized request.
2. Classify category and complexity through `rules-v1`.
3. Select the zero-cost local model policy and build context.
4. Retrieve a versioned local delivery-policy fixture and hash its evidence.
5. Produce a Pydantic-validated implementation proposal and usage estimate.

The graph uses a process-local checkpointer. The application workflow repository remains authoritative and records every completed graph state. Provider SDKs, general RAG, tools, approval, and network calls are absent.
