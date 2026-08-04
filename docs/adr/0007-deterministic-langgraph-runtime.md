# ADR-0007: Deterministic LangGraph Runtime

- Status: Accepted
- Date: 2026-08-03

## Context

Phase 3 must make agent orchestration executable and inspectable without requiring a model account, GPU, external telemetry, or provider-specific SDK. The application repository must remain authoritative even when the graph has its own checkpoint mechanism.

## Decision

Use LangGraph 1.2 behind an application-owned runtime port. The graph contains five named nodes: validation, deterministic classification, context and model-policy selection, retrieval of a versioned local policy fixture, and structured proposal generation. An in-memory LangGraph saver checkpoints the local execution thread. The API application validates the result, appends the five state transitions, and persists the aggregate using optimistic state-version checks.

The deterministic provider is a small versioned rule adapter. It returns Pydantic-validated output, estimates tokens with a stable local formula, and always records zero model cost. It cannot select or execute tools.

## Consequences

- Tests and demos require no network, credentials, GPU, or paid service.
- Graph structure and state history are explicit and testable.
- Process restart loses the graph checkpointer and in-memory repository; a durable adapter is still required before cloud operation.
- Real model adapters can replace the deterministic provider only through the structured provider port and contract suite.
- LangGraph installs `langchain-core` transitively, but high-level agent abstractions remain intentionally absent.
