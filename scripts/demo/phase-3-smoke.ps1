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

    $correlation = "phase-3-smoke"
    $headers = @{
        Authorization = "Bearer local-requester-token"
        "Idempotency-Key" = "phase-3-create"
        "X-Correlation-ID" = $correlation
    }
    $body = @{ request = "Integrate a deterministic provider API"; requestedLocale = "en" } |
        ConvertTo-Json
    $created = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/service-requests" `
        -Method Post -Headers $headers -ContentType "application/json" -Body $body
    $planHeaders = @{
        Authorization = "Bearer local-requester-token"
        "Idempotency-Key" = "phase-3-plan"
        "X-Correlation-ID" = $correlation
    }
    $planned = Invoke-RestMethod -Uri (
        "http://127.0.0.1:8080/v1/workflows/{0}/plan" -f $created.workflowId
    ) -Method Post -Headers $planHeaders
    $fetched = Invoke-RestMethod -Uri (
        "http://127.0.0.1:8080/v1/workflows/{0}" -f $created.workflowId
    ) -Headers @{ Authorization = "Bearer local-requester-token" }

    if ($planned.status -ne "awaiting_approval" -or $planned.stateVersion -ne 9) {
        throw "Deterministic planning did not reach the expected state."
    }
    if ($planned.modelPolicy.provider -ne "deterministic-local") {
        throw "Unexpected model policy."
    }
    if ($planned.metrics.estimatedCostUsd -ne 0 -or $planned.citations.Count -lt 1) {
        throw "Expected zero-cost metrics and grounded local citations."
    }
    if ($fetched.proposal.summary -ne $planned.proposal.summary) {
        throw "Stored planning result differs from the planned result."
    }

    "Phase 3 deterministic LangGraph smoke test passed."
}
finally {
    foreach ($process in $processes) {
        if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    }
    Pop-Location
}
