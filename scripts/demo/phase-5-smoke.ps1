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
            "Idempotency-Key" = "phase-5-create"
            "X-Correlation-ID" = "phase-5-flow"
        } -ContentType "application/json" -Body (@{
            request = "Integrate a protected provider API behind a typed adapter"
            requestedLocale = "en"
        } | ConvertTo-Json)
    $planned = Invoke-RestMethod -Uri (
        "http://127.0.0.1:8080/v1/workflows/{0}/plan" -f $created.workflowId
    ) -Method Post -Headers @{
        Authorization = "Bearer local-requester-token"
        "Idempotency-Key" = "phase-5-plan"
        "X-Correlation-ID" = "phase-5-flow"
    }

    if ($planned.status -ne "awaiting_approval" -or -not $planned.actionProposal) {
        throw "A passing evaluation did not produce the expected approval pause."
    }
    if ($planned.retrieval.corpusVersion -ne "local-delivery-corpus-v1") {
        throw "The versioned local corpus evidence is missing."
    }
    if ($planned.citations.Count -lt 1 -or $planned.citations[0].excerptHash.Length -ne 64) {
        throw "Grounded citation evidence is incomplete."
    }
    if ($planned.guardrails.inputOutcome -ne "passed" -or `
        $planned.guardrails.outputOutcome -ne "passed") {
        throw "The deterministic guardrail evidence is incomplete."
    }
    if (-not $planned.evaluation.passed -or $planned.evaluation.score -ne 1) {
        throw "The deterministic planning gate did not pass at the required threshold."
    }

    & (Join-Path $projectRoot "scripts\evaluation\run-golden-set.ps1")
    "Phase 5 RAG, guardrails, and evaluation-gate smoke test passed."
}
finally {
    foreach ($process in $processes) {
        if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    }
    Pop-Location
}
