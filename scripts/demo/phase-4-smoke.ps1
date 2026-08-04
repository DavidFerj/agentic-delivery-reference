[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$webRoot = Join-Path $projectRoot "apps\web-console"
$next = Join-Path $webRoot "node_modules\next\dist\bin\next"
$processes = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()

function Wait-ForEndpoint {
    param([Parameter(Mandatory)] [string] $Uri)
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { return }
        }
        catch {
            if ($attempt -eq 30) { throw "Endpoint did not become ready: $Uri" }
        }
        Start-Sleep -Milliseconds 500
    }
}

Push-Location $projectRoot
try {
    $processes.Add((Start-Process -FilePath $python -ArgumentList @(
        "-m", "uvicorn", "agentic_api.main:app", "--host", "127.0.0.1", "--port", "8080"
    ) -WindowStyle Hidden -PassThru))
    $processes.Add((Start-Process -FilePath "node" -ArgumentList @(
        $next, "start", "--hostname", "127.0.0.1", "--port", "3000"
    ) -WorkingDirectory $webRoot -WindowStyle Hidden -PassThru))
    Wait-ForEndpoint -Uri "http://127.0.0.1:8080/health"
    Wait-ForEndpoint -Uri "http://127.0.0.1:3000"

    $created = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/service-requests" `
        -Method Post -Headers @{
            Authorization = "Bearer local-requester-token"
            "Idempotency-Key" = "phase-4-create"
            "X-Correlation-ID" = "phase-4-flow"
        } -ContentType "application/json" -Body (@{
            request = "Prepare and create a governed local delivery ticket"
            requestedLocale = "en"
        } | ConvertTo-Json)
    $planned = Invoke-RestMethod -Uri (
        "http://127.0.0.1:8080/v1/workflows/{0}/plan" -f $created.workflowId
    ) -Method Post -Headers @{
        Authorization = "Bearer local-requester-token"
        "Idempotency-Key" = "phase-4-plan"
        "X-Correlation-ID" = "phase-4-flow"
    }
    if ($planned.status -ne "awaiting_approval" -or $planned.actionProposal.action -ne "create_delivery_ticket") {
        throw "Planning did not pause with a bound ticket proposal."
    }

    $approved = Invoke-RestMethod -Uri (
        "http://127.0.0.1:8080/v1/workflows/{0}/approval" -f $created.workflowId
    ) -Method Post -Headers @{
        Authorization = "Bearer local-reviewer-token"
        "Idempotency-Key" = "phase-4-approval"
        "X-Correlation-ID" = "phase-4-flow"
    } -ContentType "application/json" -Body (@{
        decision = "approved"
        reason = "The exact local proposal was reviewed."
    } | ConvertTo-Json)
    if ($approved.status -ne "approved" -or $approved.approvalDecision.consumedAt) {
        throw "The approval was not stored as an unconsumed decision."
    }

    $completed = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/local/tasks/process-next" `
        -Method Post -Headers @{
            Authorization = "Bearer local-operator-token"
            "Idempotency-Key" = "phase-4-process"
            "X-Correlation-ID" = "phase-4-flow"
        }
    if ($completed.status -ne "completed" -or $completed.stateVersion -ne 13) {
        throw "The approved task did not complete the state machine."
    }
    if (-not $completed.executionResult.simulated -or -not $completed.approvalDecision.consumedAt) {
        throw "The simulated ticket or consumed approval evidence is missing."
    }
    if ($completed.governanceDecisions.Count -ne 3) {
        throw "Tool execution did not receive its own governance decision."
    }

    "Phase 4 human approval and local asynchronous task smoke test passed."
}
finally {
    foreach ($process in $processes) {
        if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    }
    Pop-Location
}
