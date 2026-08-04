"use client";

import { FormEvent, useState } from "react";

import {
  approvalPersonas,
  dataProfiles,
  localOperatorToken,
  localPersonas,
} from "../lib/project-metadata";

type Workflow = {
  workflowId: string;
  status: string;
  correlationId: string;
  request: string;
  stateVersion?: number;
  transitions?: { from?: string | null; to: string; at: string; actorType: string }[];
  classification?: { category: string; complexity: string };
  modelPolicy?: { provider: string; model: string; reason: string };
  proposal?: { summary: string; deliverySteps: string[]; risks: string[] };
  citations?: {
    documentId: string;
    title: string;
    version: string;
    excerptHash: string;
    relevanceScore: number;
  }[];
  retrieval?: {
    corpusVersion: string;
    selectedDocumentIds: string[];
    quarantinedDocumentIds: string[];
  };
  guardrails?: {
    policyVersion: string;
    inputOutcome: string;
    retrievalOutcome: string;
    outputOutcome: string;
  };
  evaluation?: {
    gateVersion: string;
    passed: true;
    score: number;
    threshold: number;
    checks: { name: string; passed: true }[];
  };
  metrics?: { estimatedInputTokens: number; estimatedOutputTokens: number; estimatedCostUsd: number };
  governanceDecisions?: {
    decisionId: string;
    policyVersion: string;
    outcome: string;
    executionAllowed: boolean;
    classification: string;
    obligations: string[];
    retentionPolicy: string;
  }[];
  actionProposal?: {
    action: string;
    proposalDigest: string;
    schemaHash: string;
    expiresAt: string;
  };
  approvalDecision?: {
    decision: string;
    reviewerId: string;
    reason: string;
    consumedAt?: string;
  };
  executionResult?: {
    ticketId: string;
    status: string;
    simulated: boolean;
  };
};

type Problem = { detail?: string };

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8080";

export function RequestConsole() {
  const [token, setToken] = useState<string>(localPersonas[0].token);
  const [request, setRequest] = useState("");
  const [dataCategory, setDataCategory] = useState<string>(dataProfiles[0].category);
  const [approvalToken, setApprovalToken] = useState<string>(approvalPersonas[0].token);
  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setWorkflow(null);
    try {
      const correlationId = crypto.randomUUID();
      const response = await fetch(`${apiBaseUrl}/v1/service-requests`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
          "Idempotency-Key": crypto.randomUUID(),
          "X-Correlation-ID": correlationId,
        },
        body: JSON.stringify({
          request,
          requestedLocale: "en",
          dataContext: {
            declaredCategories: [dataCategory],
            purpose: "delivery_planning",
            jurisdiction: "US",
            overlayIds: ["common-us-baseline"],
          },
        }),
      });
      const payload = (await response.json()) as Workflow & Problem;
      if (!response.ok) {
        throw new Error(payload.detail ?? "The API rejected the request.");
      }
      const planResponse = await fetch(`${apiBaseUrl}/v1/workflows/${payload.workflowId}/plan`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Idempotency-Key": `plan-${payload.workflowId}`,
          "X-Correlation-ID": correlationId,
        },
      });
      const planned = (await planResponse.json()) as Workflow & Problem;
      if (!planResponse.ok) {
        throw new Error(planned.detail ?? "The deterministic planner rejected the workflow.");
      }
      setWorkflow(planned);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The API is unavailable.");
    } finally {
      setLoading(false);
    }
  }

  async function decide(current: Workflow, decision: "approved" | "rejected") {
    setActionLoading(true);
    setError("");
    try {
      const response = await fetch(`${apiBaseUrl}/v1/workflows/${current.workflowId}/approval`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${approvalToken}`,
          "Content-Type": "application/json",
          "Idempotency-Key": `approval-${current.workflowId}-${decision}`,
          "X-Correlation-ID": current.correlationId,
        },
        body: JSON.stringify({
          decision,
          reason:
            decision === "approved"
              ? "Reviewed and approved in the local console."
              : "Rejected in the local console for revision.",
        }),
      });
      const payload = (await response.json()) as Workflow & Problem;
      if (!response.ok) {
        throw new Error(payload.detail ?? "The approval decision was rejected.");
      }
      setWorkflow(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The approval API is unavailable.");
    } finally {
      setActionLoading(false);
    }
  }

  async function processTask(current: Workflow) {
    setActionLoading(true);
    setError("");
    try {
      const response = await fetch(`${apiBaseUrl}/v1/local/tasks/process-next`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localOperatorToken}`,
          "Idempotency-Key": `process-${current.workflowId}`,
          "X-Correlation-ID": current.correlationId,
        },
      });
      const payload = (await response.json()) as Workflow & Problem;
      if (!response.ok) {
        throw new Error(payload.detail ?? "The local worker rejected the task.");
      }
      setWorkflow(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The local worker is unavailable.");
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <section className="workspace" aria-labelledby="request-title">
      <div>
        <p className="eyebrow">Local authenticated journey</p>
        <h1 id="request-title">Create a delivery request</h1>
        <p className="summary">
          Choose a documented local identity and submit a request through the protected API.
        </p>
      </div>

      <form onSubmit={submit}>
        <label htmlFor="persona">Local identity</label>
        <select id="persona" value={token} onChange={(event) => setToken(event.target.value)}>
          {localPersonas.map((persona) => (
            <option key={persona.token} value={persona.token}>
              {persona.label}
            </option>
          ))}
        </select>

        <label htmlFor="data-profile">Declared data profile</label>
        <select
          id="data-profile"
          value={dataCategory}
          onChange={(event) => setDataCategory(event.target.value)}
        >
          {dataProfiles.map((profile) => (
            <option key={profile.category} value={profile.category}>
              {profile.label}
            </option>
          ))}
        </select>

        <label htmlFor="request">Service-delivery request</label>
        <textarea
          id="request"
          minLength={10}
          maxLength={10_000}
          required
          rows={7}
          value={request}
          onChange={(event) => setRequest(event.target.value)}
          placeholder="Prepare an implementation proposal for..."
        />
        <button type="submit" disabled={loading}>
          {loading ? "Submitting…" : "Submit protected request"}
        </button>
      </form>

      <div className="result" aria-live="polite">
        {error ? <p className="error">{error}</p> : null}
        {workflow ? (
          <dl>
            <div><dt>Status</dt><dd>{workflow.status}</dd></div>
            <div><dt>Workflow</dt><dd>{workflow.workflowId}</dd></div>
            <div><dt>Correlation</dt><dd>{workflow.correlationId}</dd></div>
            <div><dt>Normalized request</dt><dd>{workflow.request}</dd></div>
            {workflow.transitions ? <div><dt>State history</dt><dd><ol>{workflow.transitions.map((transition) => <li key={`${transition.to}-${transition.at}`}>{transition.to} · {transition.actorType}</li>)}</ol></dd></div> : null}
            {workflow.classification ? <div><dt>Classification</dt><dd>{workflow.classification.category} · {workflow.classification.complexity}</dd></div> : null}
            {workflow.modelPolicy ? <div><dt>Model policy</dt><dd>{workflow.modelPolicy.provider} / {workflow.modelPolicy.model}</dd></div> : null}
            {workflow.proposal ? <div><dt>Proposal</dt><dd>{workflow.proposal.summary}<ol>{workflow.proposal.deliverySteps.map((step) => <li key={step}>{step}</li>)}</ol></dd></div> : null}
            {workflow.citations ? <div><dt>Local evidence</dt><dd>{workflow.citations.map((citation) => citation.title).join(", ")}</dd></div> : null}
            {workflow.retrieval ? <div><dt>RAG evidence</dt><dd>{workflow.retrieval.corpusVersion} · {workflow.retrieval.selectedDocumentIds.length} selected · {workflow.retrieval.quarantinedDocumentIds.length} quarantined</dd></div> : null}
            {workflow.guardrails ? <div><dt>Guardrails</dt><dd>{workflow.guardrails.inputOutcome} / {workflow.guardrails.retrievalOutcome} / {workflow.guardrails.outputOutcome}<br /><small>{workflow.guardrails.policyVersion}</small></dd></div> : null}
            {workflow.evaluation ? <div><dt>Evaluation gate</dt><dd>passed · {workflow.evaluation.score.toFixed(2)} / {workflow.evaluation.threshold.toFixed(2)}<ul>{workflow.evaluation.checks.map((check) => <li key={check.name}>{check.name}: passed</li>)}</ul></dd></div> : null}
            {workflow.metrics ? <div><dt>Estimated usage</dt><dd>{workflow.metrics.estimatedInputTokens + workflow.metrics.estimatedOutputTokens} tokens · ${workflow.metrics.estimatedCostUsd.toFixed(2)}</dd></div> : null}
            {workflow.governanceDecisions ? <div><dt>Data protection</dt><dd>{workflow.governanceDecisions.at(-1)?.outcome} · {workflow.governanceDecisions.at(-1)?.classification}<ul>{workflow.governanceDecisions.at(-1)?.obligations.map((obligation) => <li key={obligation}>{obligation}</li>)}</ul></dd></div> : null}
            {workflow.actionProposal ? <div><dt>Proposed action</dt><dd>{workflow.actionProposal.action}<br /><small>Digest: {workflow.actionProposal.proposalDigest}</small></dd></div> : null}
            {workflow.approvalDecision ? <div><dt>Human decision</dt><dd>{workflow.approvalDecision.decision} by {workflow.approvalDecision.reviewerId}<br />{workflow.approvalDecision.reason}</dd></div> : null}
            {workflow.executionResult ? <div><dt>Simulated ticket</dt><dd>{workflow.executionResult.ticketId} / {workflow.executionResult.status}</dd></div> : null}
          </dl>
        ) : null}
        {workflow?.status === "awaiting_approval" ? (
          <div className="actions">
            <label htmlFor="approval-persona">Approval identity</label>
            <select id="approval-persona" value={approvalToken} onChange={(event) => setApprovalToken(event.target.value)}>
              {approvalPersonas.map((persona) => <option key={persona.token} value={persona.token}>{persona.label}</option>)}
            </select>
            <button type="button" disabled={actionLoading} onClick={() => void decide(workflow, "approved")}>Approve exact proposal</button>
            <button type="button" className="secondary" disabled={actionLoading} onClick={() => void decide(workflow, "rejected")}>Reject proposal</button>
          </div>
        ) : null}
        {workflow?.status === "approved" ? (
          <div className="actions">
            <p>The approval is stored. Processing is a separate idempotent delivery.</p>
            <button type="button" disabled={actionLoading} onClick={() => void processTask(workflow)}>Process queued task</button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
