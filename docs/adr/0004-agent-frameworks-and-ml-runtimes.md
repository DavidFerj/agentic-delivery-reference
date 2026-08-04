# ADR-0004: LangGraph, Selective LangChain, and Optional ML Runtimes

- Status: Accepted
- Date: 2026-08-03

## Context

The workflow needs durable state, explicit control, human interruption, retrieval, and replaceable model providers. Full model training is outside the MVP.

## Decision

Use LangGraph for explicit orchestration, checkpoint boundaries, interruption, resumption, and state routing. Use LangChain selectively for document processing, retrieval components, model/message interoperability, and tool adaptation when it reduces code without hiding domain behavior.

Do not include TensorFlow. Do not include PyTorch in the API or base worker image. A future optional local-embeddings profile may use PyTorch in the ingestion or embedding workload when a measured need justifies the image and resource cost.

## Consequences

- Agent state and transitions remain inspectable.
- The system runs with a deterministic provider and without GPU dependencies.
- LangChain abstractions are isolated behind application ports where provider lock-in is possible.
- Semantic local retrieval may be less capable until the optional embedding profile is added.
