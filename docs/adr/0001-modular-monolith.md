# ADR-0001: Modular Monolith with Four Deployables

- Status: Accepted
- Date: 2026-08-03

## Context

The reference must demonstrate multiple capabilities without becoming a distributed monolith or hiding unrelated responsibilities in one process.

## Decision

Use one monorepo and one modular application architecture with four deployment boundaries: web, API, private worker, and evaluator job. Backend modules communicate through application contracts inside the process. Separate deployment is introduced only for user experience, interactive API, asynchronous work, and batch evaluation lifecycles.

## Consequences

- Local setup and end-to-end testing remain manageable.
- Web, API, worker, and evaluation workloads scale independently.
- Module boundaries require import and architecture tests.
- A module may be extracted later only with demonstrated deployment, scaling, security, ownership, or lifecycle need.

## Rejected alternatives

- One deployable for every capability: excessive operational coupling and cost.
- One undifferentiated application process: asynchronous and batch lifecycles would be obscured.
