import { RequestConsole } from "../components/request-console";
import { projectPhase } from "../lib/project-metadata";

export default function Home() {
  return (
    <main>
      <header className="topbar">
        <strong>Agentic Delivery Reference</strong>
        <span className="status">{projectPhase}</span>
      </header>
      <RequestConsole />
      <aside className="notice">
        Every API response is correlated and protected by defensive headers. Sanitized telemetry,
        structured audit evidence, readiness, RBAC, rate limits, guardrails, and evaluation gates
        are active locally; external integrations remain disabled.
      </aside>
    </main>
  );
}
