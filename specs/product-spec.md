# Product Specification

## Document control

- Product: Agentic Service Delivery Hub
- Repository: Agentic Delivery Reference
- Version: 0.1
- Status: Phases 0–6 locally verified
- Primary decision-maker: Product owner

## Problem

Teams evaluating agentic AI frequently see isolated demos that omit delivery controls, durable state, security, evaluation, cost, and operational evidence. This project must demonstrate those concerns as one small, executable, production-shaped system.

## Product objective

Provide a reference workflow that converts a service or software-delivery request into a grounded implementation proposal and a governed delivery-ticket action, while preserving state, approval decisions, traceability, evaluation evidence, and cost estimates.

## Target users

| Persona | Need |
| --- | --- |
| Requester | Submit a request and understand its outcome |
| Reviewer | Review, approve, edit, or reject sensitive actions |
| Operator | Diagnose executions and safely recover failures |
| Administrator | Manage access and inspect security/audit evidence |
| Engineer | Study, run, test, and extend the reference implementation |

## Primary journey

1. An authenticated requester submits a service-delivery request.
2. The API validates and stores it.
3. The runtime classifies the request and selects a model policy.
4. The runtime retrieves relevant knowledge and records citations.
5. The runtime produces a structured implementation proposal and complexity estimate.
6. A simulated ticket tool call is proposed.
7. The workflow pauses for an authorized human decision.
8. Approval resumes the workflow; rejection terminates the proposed action safely.
9. The worker executes the simulated action idempotently.
10. Evaluators score the result and compare it with a baseline.
11. The console shows the result, state history, evidence, audit events, latency, token estimate, and estimated cost.

## MVP scope

The first reference release includes:

- Web console and protected API
- Deterministic local model provider and optional real-provider ports
- Explicit LangGraph workflow
- Local knowledge base and grounded retrieval
- Session memory and durable workflow state
- Typed, governed tool proposals
- Human approval for ticket creation
- Asynchronous execution with retry and idempotency semantics
- Structured audit events, logs, traces, and operational metrics
- Golden-set evaluation and security-focused cases
- Local Docker profile and documented GCP deployment profile

## Out of scope

- Commercial multi-tenant SaaS capabilities
- Autonomous destructive actions
- Training or fine-tuning foundation models
- Mandatory GPU execution
- Mandatory paid services
- Real n8n, Vapi, ticketing, MCP, or LLM-provider integration in the initial delivery
- Production deployment or production data migration
- Claims of interoperability without reproducible tests

## Product principles

- Every capability has a visible purpose and verifiable evidence.
- Sensitive side effects require explicit authorization.
- Deterministic behavior is available without paid services.
- Provider-specific behavior remains outside the application core.
- A failed or duplicated delivery must not create duplicate side effects.
- Documentation never substitutes for runtime or test evidence.

## Success measures

| Metric | Initial target |
| --- | --- |
| Local setup success | One documented workflow on a clean supported machine |
| Main demo duration | Under 10 minutes after setup |
| Golden-set deterministic pass rate | 100% |
| Unauthorized sensitive actions | 0 |
| Duplicate side effects under retry | 0 |
| Trace completeness | 100% of workflow executions have a correlation ID |
| Capability evidence coverage | 100% of capabilities claimed as implemented |

## Assumptions

- English is the repository and public documentation language.
- Local mode is the default and uses synthetic data.
- GCP is the target cloud platform.
- Firebase Authentication and Firestore are the target identity and operational-state services.
- External integration credentials will be supplied only in a later authorized phase.

## Release boundary

The first release is ready when all criteria in [v1 acceptance criteria](acceptance-criteria/v1.md) are verified and every implemented capability is traceable through `capability-map.yaml`.
