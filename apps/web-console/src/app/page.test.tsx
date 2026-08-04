import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import Home from "./page";

const workflow = {
  workflowId: "workflow-1",
  status: "awaiting_approval",
  correlationId: "correlation-1",
  request: "Prepare a delivery proposal",
  transitions: [
    { from: null, to: "received", at: "2026-08-04T12:00:00Z", actorType: "user" },
    {
      from: "evaluated",
      to: "awaiting_approval",
      at: "2026-08-04T12:00:01Z",
      actorType: "system",
    },
  ],
  classification: { category: "general", complexity: "low" },
  modelPolicy: { provider: "deterministic-local", model: "rules-v1", reason: "local" },
  proposal: {
    summary: "A deterministic implementation proposal",
    deliverySteps: ["Define contracts.", "Implement the vertical slice."],
    risks: ["Requirements may change."],
  },
  citations: [
    {
      documentId: "policy",
      title: "Local delivery policy",
      version: "1.0.0",
      excerptHash: "abc123",
      relevanceScore: 1,
    },
  ],
  retrieval: {
    corpusVersion: "local-delivery-corpus-v1",
    selectedDocumentIds: ["policy"],
    quarantinedDocumentIds: [],
  },
  guardrails: {
    policyVersion: "local-guardrails-v1",
    inputOutcome: "passed",
    retrievalOutcome: "passed",
    outputOutcome: "passed",
  },
  evaluation: {
    gateVersion: "local-evaluation-gate-v1",
    passed: true,
    score: 1,
    threshold: 1,
    checks: [
      { name: "structured_output", passed: true },
      { name: "grounded_guidance", passed: true },
    ],
  },
  metrics: { estimatedInputTokens: 8, estimatedOutputTokens: 20, estimatedCostUsd: 0 },
  governanceDecisions: [
    {
      decisionId: "decision-1",
      policyVersion: "common-us-v1",
      outcome: "permit_with_controls",
      executionAllowed: true,
      classification: "restricted_personal_data",
      obligations: ["audit_decision", "local_processing_only"],
      retentionPolicy: "restricted-30-days",
    },
  ],
  actionProposal: {
    action: "create_delivery_ticket",
    proposalDigest: "abc123",
    schemaHash: "schema123",
    expiresAt: "2026-08-04T12:30:00Z",
  },
};

const receivedWorkflow = { ...workflow, status: "received" };
const approvedWorkflow = {
  ...workflow,
  status: "approved",
  approvalDecision: {
    decision: "approved",
    reviewerId: "local-reviewer",
    reason: "Reviewed and approved in the local console.",
  },
};
const completedWorkflow = {
  ...approvedWorkflow,
  status: "completed",
  approvalDecision: { ...approvedWorkflow.approvalDecision, consumedAt: "2026-08-04T12:05:00Z" },
  executionResult: { ticketId: "LOCAL-ABC123", status: "created", simulated: true },
};
const rejectedWorkflow = {
  ...workflow,
  status: "rejected",
  approvalDecision: {
    decision: "rejected",
    reviewerId: "local-reviewer",
    reason: "Rejected in the local console for revision.",
  },
};

function fillAndSubmit(request = "Prepare a delivery proposal") {
  fireEvent.change(screen.getByLabelText("Service-delivery request"), {
    target: { value: request },
  });
  fireEvent.submit(
    screen.getByRole("button", { name: /Submit protected request|Submitting/ }).closest("form")!,
  );
}

describe("governed delivery request page", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("submits declared data context and renders the policy decision", async () => {
    let resolveFetch!: (value: Response) => void;
    const fetchPromise = new Promise<Response>((resolve) => {
      resolveFetch = resolve;
    });
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(fetchPromise)
      .mockResolvedValueOnce(new Response(JSON.stringify(workflow), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    render(<Home />);
    expect(screen.getByText("Phase 6 / Security and operational hardening")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Local identity"), {
      target: { value: "local-administrator-token" },
    });
    fireEvent.change(screen.getByLabelText("Declared data profile"), {
      target: { value: "health_information" },
    });
    fillAndSubmit();
    expect(screen.getByRole("button", { name: "Submitting…" })).toBeTruthy();

    resolveFetch(new Response(JSON.stringify(receivedWorkflow), { status: 202 }));
    await waitFor(() => expect(screen.getByText("workflow-1")).toBeTruthy());

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8080/v1/service-requests",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer local-administrator-token",
        }),
      }),
    );
    const createOptions = fetchMock.mock.calls[0]![1] as RequestInit;
    expect(JSON.parse(createOptions.body as string)).toEqual(
      expect.objectContaining({
        dataContext: expect.objectContaining({
          declaredCategories: ["health_information"],
          overlayIds: ["common-us-baseline"],
        }),
      }),
    );
    expect(screen.getByText("correlation-1")).toBeTruthy();
    expect(screen.getByText("awaiting_approval · system")).toBeTruthy();
    expect(screen.getByText("general · low")).toBeTruthy();
    expect(screen.getByText("deterministic-local / rules-v1")).toBeTruthy();
    expect(screen.getByText("A deterministic implementation proposal")).toBeTruthy();
    expect(screen.getByText("Local delivery policy")).toBeTruthy();
    expect(screen.getByText(/local-delivery-corpus-v1/)).toBeTruthy();
    expect(screen.getByText("passed / passed / passed")).toBeTruthy();
    expect(screen.getByText(/passed · 1.00 \/ 1.00/)).toBeTruthy();
    expect(screen.getByText("grounded_guidance: passed")).toBeTruthy();
    expect(screen.getByText("28 tokens · $0.00")).toBeTruthy();
    expect(screen.getByText(/permit_with_controls/)).toBeTruthy();
    expect(screen.getByText("local_processing_only")).toBeTruthy();
    expect(screen.getByText("create_delivery_ticket")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Submit protected request" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Approve exact proposal" })).toBeTruthy();
  });

  it("approves the exact proposal and processes the queued local task", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(receivedWorkflow), { status: 202 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(workflow), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(approvedWorkflow), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(completedWorkflow), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    fillAndSubmit();
    await waitFor(() => expect(screen.getByRole("button", { name: "Approve exact proposal" })).toBeTruthy());
    fireEvent.change(screen.getByLabelText("Approval identity"), {
      target: { value: "local-administrator-token" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Approve exact proposal" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Process queued task" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Process queued task" }));
    await waitFor(() => expect(screen.getByText(/LOCAL-ABC123/)).toBeTruthy());

    expect(fetchMock.mock.calls[2]![0]).toContain("/workflow-1/approval");
    expect(fetchMock.mock.calls[2]![1]).toEqual(
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer local-administrator-token",
        }),
      }),
    );
    expect(JSON.parse(fetchMock.mock.calls[2]![1]!.body as string).decision).toBe("approved");
    expect(fetchMock.mock.calls[3]![0]).toContain("/v1/local/tasks/process-next");
    expect(screen.getByText(/approved by local-reviewer/)).toBeTruthy();
  });

  it("records a human rejection without presenting task processing", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(receivedWorkflow), { status: 202 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(workflow), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(rejectedWorkflow), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    fillAndSubmit();
    await waitFor(() => expect(screen.getByRole("button", { name: "Reject proposal" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Reject proposal" }));
    await waitFor(() => expect(screen.getByText(/rejected by local-reviewer/)).toBeTruthy());

    expect(JSON.parse(fetchMock.mock.calls[2]![1]!.body as string).decision).toBe("rejected");
    expect(screen.queryByRole("button", { name: "Process queued task" })).toBeNull();
  });

  it("shows safe approval failures for API and transport errors", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(receivedWorkflow), { status: 202 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(workflow), { status: 200 }))
      .mockResolvedValueOnce(new Response("{}", { status: 500 }))
      .mockRejectedValueOnce("offline");
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    fillAndSubmit();
    await waitFor(() => expect(screen.getByRole("button", { name: "Approve exact proposal" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Approve exact proposal" }));
    await waitFor(() => expect(screen.getByText("The approval decision was rejected.")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Reject proposal" }));
    await waitFor(() => expect(screen.getByText("The approval API is unavailable.")).toBeTruthy());
  });

  it("shows safe worker failures for API and transport errors", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(receivedWorkflow), { status: 202 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(workflow), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(approvedWorkflow), { status: 200 }))
      .mockResolvedValueOnce(new Response("{}", { status: 500 }))
      .mockRejectedValueOnce("offline");
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    fillAndSubmit();
    await waitFor(() => expect(screen.getByRole("button", { name: "Approve exact proposal" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Approve exact proposal" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Process queued task" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Process queued task" }));
    await waitFor(() => expect(screen.getByText("The local worker rejected the task.")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Process queued task" }));
    await waitFor(() => expect(screen.getByText("The local worker is unavailable.")).toBeTruthy());
  });

  it("shows an actionable API problem and clears an earlier result", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(receivedWorkflow), { status: 202 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(workflow), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(receivedWorkflow), { status: 202 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "The current role cannot create requests." }), {
          status: 403,
        }),
      );
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    fillAndSubmit();
    await waitFor(() => expect(screen.getByText("workflow-1")).toBeTruthy());
    fillAndSubmit("Prepare another delivery proposal");

    await waitFor(() =>
      expect(screen.getByText("The current role cannot create requests.")).toBeTruthy(),
    );
    expect(screen.queryByText("workflow-1")).toBeNull();
  });

  it("handles malformed create problems and unavailable transports", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("{}", { status: 500 }))
      .mockRejectedValueOnce("offline");
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    fillAndSubmit();
    await waitFor(() => expect(screen.getByText("The API rejected the request.")).toBeTruthy());
    fillAndSubmit("Prepare one more delivery proposal");
    await waitFor(() => expect(screen.getByText("The API is unavailable.")).toBeTruthy());
  });

  it("handles a minimal planned response and a malformed planner problem", async () => {
    const minimal = {
      workflowId: "workflow-minimal",
      status: "planned",
      correlationId: "correlation-minimal",
      request: "Prepare a minimal proposal",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(receivedWorkflow), { status: 202 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(minimal), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(receivedWorkflow), { status: 202 }))
      .mockResolvedValueOnce(new Response("{}", { status: 500 }));
    vi.stubGlobal("fetch", fetchMock);
    render(<Home />);

    fillAndSubmit("Prepare a minimal proposal");
    await waitFor(() => expect(screen.getByText("workflow-minimal")).toBeTruthy());
    fillAndSubmit("Prepare a planner failure case");
    await waitFor(() =>
      expect(screen.getByText("The deterministic planner rejected the workflow.")).toBeTruthy(),
    );
  });
});
