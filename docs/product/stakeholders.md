# Stakeholders and Decisions

| Role | Responsibility | Key decisions |
| --- | --- | --- |
| Product owner | Defines desired behavior and accepts outcomes | Scope, priorities, acceptance |
| Engineering | Designs and implements the system | Architecture and implementation trade-offs |
| Security reviewer | Challenges trust boundaries and controls | Blocking findings and risk acceptance |
| Quality reviewer | Verifies requirements and evidence | Test sufficiency and release gates |
| Operator | Validates diagnostics and recovery | Runbook usability and operational readiness |
| Repository consumer | Runs and studies the reference | Setup clarity and capability discoverability |

The product owner is the final decision-maker for functional scope. Security findings that permit unauthorized access, data exposure, privilege escalation, destructive behavior, or secret compromise block release until mitigated or explicitly resolved through a documented scope decision.
