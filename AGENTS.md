# Repository Instructions

## Source of truth

The approved product behavior is defined under `specs/`. Requirements use `FR-*` and `NFR-*`; acceptance criteria use `AC-*`. Do not change those behaviors merely to simplify implementation.

## Architecture

- Preserve the modular-monolith decision in ADR-0001.
- Keep routes thin and application use cases explicit.
- Domain and application modules must not import cloud or provider SDKs.
- Access external systems only through typed ports and validated adapters.
- Do not claim an integration or capability without reproducible evidence.
- Keep long-running and retryable work outside interactive HTTP execution.

## Security

- Treat user input, retrieved content, model output, tool arguments, and provider responses as untrusted.
- Enforce authentication, authorization, and resource ownership server-side.
- Never commit or log secrets, tokens, credentials, personal data, or production data.
- Sensitive side effects require a valid approval bound to the proposal digest.
- Preserve idempotency and optimistic-concurrency invariants.

## Quality

- Derive tests from acceptance criteria and failure modes.
- Target 100% statement and branch coverage for new or modified business logic where meaningful.
- Run formatting, linting, type checking, tests, security checks, evaluation gates, and builds before completion.
- Keep `capability-map.yaml` synchronized with implementation and evidence.

## Delivery

- Local mode must work without paid external services.
- Production deployment and data changes require explicit authorization.
- Do not commit, push, create a pull request, or deploy unless explicitly requested.
