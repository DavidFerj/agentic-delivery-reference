# ADR-0005: Phase 1 Toolchain Baseline

- Status: Accepted
- Date: 2026-08-03

## Context

The monorepo needs reproducible local and CI workflows across a strict TypeScript frontend and typed Python services. The current development machine provides Node.js 24 and Python 3.14 but not Docker.

## Decision

- Use Node.js 24, pnpm 11, Next.js 16, React 19, TypeScript, ESLint, Vitest, and Testing Library for the web console.
- Support Python 3.12 through 3.14 and use FastAPI, Pydantic Settings, Uvicorn, Ruff, mypy, pytest, and coverage for the Python deployables.
- Use one Python distribution with explicitly discoverable service packages while preserving separate process entry points.
- Use Docker Compose as the container profile and native PowerShell commands as an equally supported local profile.
- Do not add LangGraph, LangChain, PyTorch, TensorFlow, cloud SDKs, or external-provider SDKs until a phase implements behavior requiring them.

## Consequences

- The dependency graph stays small during foundation work.
- Native Windows validation can proceed without changing system execution policy or installing Docker Desktop.
- Docker builds were initially deferred in Phase 1 and were later verified on Docker Desktop with the WSL 2 backend after Phase 3.5.
- Later phases must add and justify AI and cloud dependencies at their actual integration boundary.
