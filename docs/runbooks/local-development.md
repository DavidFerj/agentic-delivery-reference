# Local Development Runbook

## Supported baseline

- Git 2.55 or newer
- Node.js 24
- pnpm 11
- Python 3.12 through 3.14
- Docker Desktop with Compose v2 for the container profile

The project is validated natively on Windows and with Docker Desktop using the WSL 2 backend. The verified container profile uses Docker Desktop 4.85, Engine 29.6, and Compose 5.3; compatible newer versions may also work but require validation.

## Bootstrap on Windows

```powershell
Copy-Item .env.example .env
powershell -ExecutionPolicy Bypass -File scripts/setup/bootstrap.ps1
```

The `.env` file is ignored by Git. Do not place real credentials in local files unless a later integration runbook explicitly requires them.

## Run quality checks

```powershell
powershell -ExecutionPolicy Bypass -File scripts/quality/check.ps1
```

## Run services natively

Use separate terminals from the repository root.

API:

```powershell
.venv\Scripts\python -m uvicorn agentic_api.main:app --host 127.0.0.1 --port 8080
```

Worker:

```powershell
.venv\Scripts\python -m uvicorn agentic_worker.main:app --host 127.0.0.1 --port 8081
```

Web console:

```powershell
pnpm.cmd web:dev
```

Evaluator foundation check:

```powershell
.venv\Scripts\agentic-evaluator
```

Automated native smoke test after building the web console:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/demo/foundation-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-2-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-3-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-3-5-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-4-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-5-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/demo/phase-6-smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts/evaluation/run-golden-set.ps1
powershell -ExecutionPolicy Bypass -File scripts/security/run-red-team.ps1
```

## Run with Docker Compose

```powershell
docker compose up --build
```

Run the evaluator job:

```powershell
docker compose --profile tools run --rm evaluator
```

Stop the local stack:

```powershell
docker compose down
```

Run the complete reproducible container validation, which always removes its containers and network:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/demo/containerized-smoke.ps1
```

## Expected endpoints

- Web: `http://localhost:3000`
- API health: `http://localhost:8080/health`
- API documentation outside production: `http://localhost:8080/docs`
- Protected session: `http://localhost:8080/v1/session`
- Worker health: `http://localhost:8081/health`

## Troubleshooting

- If PowerShell blocks `npm.ps1`, use `npm.cmd` or `pnpm.cmd`; do not relax the machine execution policy.
- If a port is occupied, stop the conflicting process or set the corresponding value in `.env` for Compose.
- If `.venv` is missing, rerun the bootstrap script.
- If a quality gate fails, fix the source or configuration; do not lower its threshold.

## Phase 2 local identities

The console offers four documented local fixtures: requester, reviewer, operator, and administrator. They exercise the authentication and RBAC boundary but are not secrets and provide no production security. The API refuses to start with this adapter when `ADR_ENVIRONMENT=production`.

Workflow state is process-local in Phase 2 and is cleared whenever the API restarts. This limitation is deliberate; use the repository port rather than depending on adapter behavior when extending the application.

## Phase 3 deterministic planning

Create a request in the web console. The console then calls the protected `/v1/workflows/{workflow_id}/plan` endpoint and displays the graph result. LangGraph and the API repository both use process-local state; restarting the API clears it. No provider key, LangSmith account, GPU, PyTorch, or TensorFlow is required.

## Phase 3.5 data-protection control plane

`ADR_GOVERNANCE_MODE=enforce` is the safe default. Use `observe` or `warn` only to assess a legacy migration; a deny decision is still recorded but does not block in those modes. The console declares a data category, and the API evaluates policy before storing the workflow and before invoking the local planner. Only `common-us-baseline` is active. Industry overlay templates are rejected until reviewed and implemented.

## Phase 4 human approval and local tasks

Submit a request as the local requester. Planning pauses in `awaiting_approval` with a schema hash, digest, and expiry. Use the separate reviewer identity to approve or reject. An approval enqueues work but does not create a ticket. Select **Process queued task** to exercise the operator boundary, execution-time data policy, one-time approval consumption, and idempotent simulated ticket.

The queue and all records are process-memory adapters. Restarting the API clears them. This profile demonstrates contracts and delivery semantics without claiming durable Cloud Tasks or n8n integration.

## Phase 5 RAG, guardrails, and evaluation gates

Planning retrieves up to two passages from `evaluations/golden-set`-independent, versioned synthetic knowledge embedded in the runtime. Each citation includes its document version, relevance score, and SHA-256 passage hash. Retrieved text is scanned and quarantined before it becomes context.

The runtime blocks recognized instruction-override patterns in user input, checks generated output, and requires a 100% deterministic structure, grounding, integrity, and safety score before it creates an approval proposal. Run `scripts/evaluation/run-golden-set.ps1` to execute normal and adversarial release cases. This local gate does not claim semantic retrieval, comprehensive jailbreak detection, or LLM-as-judge behavior.

## Phase 6 security and operational hardening

`/health` reports process liveness and `/ready` reports named local component readiness. Every response returns `X-Correlation-ID`, defensive browser headers, and `Cache-Control: no-store`. Invalid correlation values are rejected before route execution.

An operator or administrator can inspect sanitized aggregate request evidence at `/v1/operations/metrics`; only an administrator can inspect `/v1/operations/audit-events`. These endpoints never include request bodies, prompts, authorization values, idempotency keys, or response payloads. Mutable operations use `ADR_RATE_LIMIT_REQUESTS` within `ADR_RATE_LIMIT_WINDOW_SECONDS` per verified local principal.

Run `scripts/security/run-red-team.ps1` for the deterministic abuse suite. All operational state is in memory and clears on restart; multi-replica rate limits, durable audit storage, OpenTelemetry export, SIEM, and managed monitoring remain cloud adapters.
