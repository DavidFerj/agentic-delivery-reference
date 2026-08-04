# Agentic Delivery Reference

> A production-shaped reference implementation for building, evaluating, securing, and operating agentic AI systems across the complete software delivery lifecycle.

## Status

Phases 0 through 7 are complete. The local system verifies authenticated and grounded planning, executable data protection, prompt-injection guardrails, deterministic evaluation gates, bound human approval, asynchronous execution, and security-hardened operational evidence. Phase 7 adds structurally verified, plan-only Google Cloud infrastructure and delivery automation; no cloud project or resource has been created.

## Business scenario

A requester asks the system to prepare an implementation proposal, estimate delivery complexity, and create a delivery ticket. The system validates the request, retrieves supporting knowledge, produces a structured plan, proposes a governed tool action, waits for human approval, and records the result with complete audit evidence.

## Target architecture

The project is a monorepo built around a moderately modular architecture with four planned deployables:

- Next.js web console
- FastAPI backend API
- Private asynchronous worker
- Evaluation job

The agent runtime will use LangGraph for explicit workflow orchestration and selected LangChain components for retrieval and provider interoperability. External systems such as n8n, Vapi, MCP servers, ticketing platforms, and real model providers remain behind disabled ports and simulated adapters until a later phase.

See [the architecture overview](docs/architecture/overview.md) and [the product specification](specs/product-spec.md).

## Phase roadmap

| Phase | Outcome | Status |
| --- | --- | --- |
| 0 | Product specification, architecture, contracts, test plan, and threat model | Complete |
| 1 | Repository foundation, local containers, quality tooling, and CI | Complete |
| 2 | Authenticated web/API vertical slice | Complete |
| 3 | Deterministic agent runtime | Complete |
| 3.5 | Data classification, policy decisions, obligations, and industry overlay extension points | Complete |
| 4 | Human approval and asynchronous execution | Complete |
| 5 | RAG, guardrails, and evaluation gates | Complete |
| 6 | Security and operational hardening | Complete |
| 7 | Plan-only GCP infrastructure, adapter bindings, CI/CD, and guarded deployment automation | Complete |
| 8 | External integration readiness | Planned |
| 9 | Public reference release | Planned |

## Specification index

- [Product specification](specs/product-spec.md)
- [Functional requirements](specs/requirements/functional-requirements.md)
- [Non-functional requirements](specs/requirements/non-functional-requirements.md)
- [Acceptance criteria](specs/acceptance-criteria/v1.md)
- [Phase 3.5 acceptance criteria](specs/acceptance-criteria/phase-3-5.md)
- [Phase 4 acceptance criteria](specs/acceptance-criteria/phase-4.md)
- [Phase 5 acceptance criteria](specs/acceptance-criteria/phase-5.md)
- [Phase 6 acceptance criteria](specs/acceptance-criteria/phase-6.md)
- [Phase 7 acceptance criteria](specs/acceptance-criteria/phase-7.md)
- [System design](specs/design/system-design.md)
- [Workflow state model](specs/design/workflow-state-model.md)
- [Test plan](specs/test-plan/test-plan.md)
- [Threat model](specs/threat-model/threat-model.md)
- [Capability registry](capability-map.yaml)

## Local foundation

The Phase 1 foundation requires Node.js 24, pnpm 11, and Python 3.12–3.14. On Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup/bootstrap.ps1
powershell -ExecutionPolicy Bypass -File scripts/quality/check.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/foundation-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-2-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-3-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-3-5-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-4-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-5-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-6-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-7-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/infra/validate-gcp-readiness.ps1 -SkipTerraform
powershell -ExecutionPolicy Bypass -File scripts/evaluation/run-golden-set.ps1
powershell -ExecutionPolicy Bypass -File scripts/security/run-red-team.ps1
```

See the [local development runbook](docs/runbooks/local-development.md) for native and Docker Compose workflows.

The native Windows and Docker Desktop/WSL 2 profiles are verified. The container suite builds and runs the web, API, worker, evaluator, governed workflow, operational evidence, and required security/evaluation gates through Phase 7. See the [container validation evidence](evaluations/reports/containerized-local-validation.json).

## Explicit limitations

- No external provider is integrated in Phase 0.
- Phase 2 identity values and in-memory state are local adapters, not production services.
- Phase 3 planning uses a rules-based structured provider, one local policy fixture, and process-local LangGraph checkpoints.
- Phase 3.5 classification uses conservative local rules, not production DLP; the baseline is not legal advice or certification, and sector overlays remain disabled pending legal/compliance review.
- Phase 4 uses process-memory workflow, queue, approval, audit, and execution adapters. The ticket is simulated; durable storage, Cloud Tasks, n8n, and real ticket providers remain future adapters.
- Phase 5 RAG is deterministic lexical retrieval over a small synthetic corpus. Pattern guardrails are deliberately narrow and are not a comprehensive jailbreak detector. The evaluation gate is rules-based; semantic embeddings, vector databases, and LLM-as-judge remain optional future adapters.
- Phase 6 telemetry, audit, readiness, and rate-limit adapters are process-local. They demonstrate safe schemas and control placement but do not replace distributed rate limiting, durable audit storage, OpenTelemetry collection, SIEM integration, or managed cloud monitoring.
- Phase 7 is deployment preparation only. Terraform defaults to an empty managed-resource graph, the Python GCP adapter manifest performs no provider calls, and the cloud profile is not activated. Project creation, billing linkage, remote state bootstrap, provider adapter implementation, Workload Identity Federation bootstrap, plan approval, and deployment require separate authorization.
- No cloud resource is provisioned or deployed in Phase 0.
- No compatibility claim is made for a coding agent without reproducible evidence.
- LLM-as-judge, semantic embeddings, voice, MCP, n8n, and real ticket creation are future adapters.

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).
