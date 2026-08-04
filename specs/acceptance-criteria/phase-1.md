# Phase 1 Acceptance Criteria

- **AC1-001:** Given supported Python, when the project is installed in a virtual environment, then API, worker, evaluator, test, lint, type, and repository-validation commands are available.
- **AC1-002:** Given supported Node.js and pnpm, when dependencies are installed, then the web console can be linted, type checked, tested, built, and started.
- **AC1-003:** Given the API process, when `/health` is requested, then it returns a minimal successful response without secrets or dependency details.
- **AC1-004:** Given the private worker process, when `/health` is requested, then it reports liveness while exposing no documentation or placeholder task endpoint.
- **AC1-005:** Given the evaluator entry point, when it runs, then it emits deterministic machine-readable foundation status without claiming runtime evaluation support.
- **AC1-006:** Given Docker Compose, then it declares web, API, worker, and optional evaluator boundaries with health checks for long-running services.
- **AC1-007:** Given `.env.example`, then local defaults contain no secrets and all external integrations are disabled.
- **AC1-008:** Given the repository validator, when contracts, links, capability paths, identifiers, Compose structure, and secret patterns are valid, then it exits successfully.
- **AC1-009:** Given CI configuration, then Python quality, web quality, dependency auditing, and Compose validation are required without cloud deployment credentials.
- **AC1-010:** Given the local foundation smoke workflow, then web, API, worker, and evaluator foundations execute without n8n, Vapi, MCP, LangGraph, LangChain, a real model, or a paid service.
