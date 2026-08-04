# User Journey

| Stage | Requester experience | System behavior | Evidence |
| --- | --- | --- | --- |
| Sign in | Establish identity | Verify OIDC token and role | Authentication event |
| Submit | Describe desired delivery outcome | Validate, normalize, persist | Request and correlation ID |
| Plan | Observe progress | Classify, retrieve, plan | State history and citations |
| Review | Wait for governed action | Pause on sensitive tool proposal | Approval proposal and digest |
| Decide | Reviewer approves or rejects | Authorize and consume one decision | Actor, decision, timestamp |
| Execute | Observe final processing | Run idempotent simulated ticket tool | Tool execution record |
| Understand | Review proposal and evidence | Evaluate and aggregate telemetry | Scores, latency, tokens, cost |

## Failure journeys

- Invalid input remains editable and creates no workflow.
- Unauthorized access reveals no protected resource details.
- Provider failure records a safe reason and a recoverable or terminal state.
- Rejected approval produces no side effect.
- Duplicate worker delivery returns the original side-effect result.
