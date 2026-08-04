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

    $health = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" `
        -UseBasicParsing -Headers @{ "X-Correlation-ID" = "phase-6-health" }
    $ready = Invoke-RestMethod -Uri "http://127.0.0.1:8080/ready"
    if ($health.Headers["X-Correlation-ID"] -ne "phase-6-health" -or `
        $health.Headers["X-Content-Type-Options"] -ne "nosniff") {
        throw "Correlation or defensive response headers are missing."
    }
    if ($ready.status -ne "ready" -or $ready.checks.telemetry -ne "ready") {
        throw "Readiness does not report the local operational components."
    }

    $created = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/service-requests" `
        -Method Post -Headers @{
            Authorization = "Bearer local-requester-token"
            "Idempotency-Key" = "phase-6-create"
            "X-Correlation-ID" = "phase-6-flow"
        } -ContentType "application/json" -Body (@{
            request = "Prepare a secure and observable local delivery plan"
            requestedLocale = "en"
        } | ConvertTo-Json)
    $planned = Invoke-RestMethod -Uri (
        "http://127.0.0.1:8080/v1/workflows/{0}/plan" -f $created.workflowId
    ) -Method Post -Headers @{
        Authorization = "Bearer local-requester-token"
        "Idempotency-Key" = "phase-6-plan"
        "X-Correlation-ID" = "phase-6-flow"
    }
    if ($planned.status -ne "awaiting_approval" -or -not $planned.evaluation.passed) {
        throw "The secured workflow did not reach its approval boundary."
    }

    $metrics = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/operations/metrics" `
        -Headers @{
            Authorization = "Bearer local-operator-token"
            "X-Correlation-ID" = "phase-6-metrics"
        }
    $audit = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/operations/audit-events?limit=10" `
        -Headers @{
            Authorization = "Bearer local-administrator-token"
            "X-Correlation-ID" = "phase-6-audit"
        }
    if ($metrics.totalRequests -lt 4 -or $metrics.recentRequests.Count -lt 1) {
        throw "Sanitized operational metrics are incomplete."
    }
    $lastAudit = $audit.events[-1]
    if ($lastAudit.action -ne "operations.audit.read" -or `
        $lastAudit.correlationId -ne "phase-6-audit" -or -not $lastAudit.occurredAt) {
        throw "Structured audit evidence is incomplete."
    }
    $serialized = $metrics | ConvertTo-Json -Depth 8
    if ($serialized -match "local-operator-token|Authorization|Idempotency-Key") {
        throw "Sensitive transport metadata leaked into operational evidence."
    }

    & (Join-Path $projectRoot "scripts\security\run-red-team.ps1")
    "Phase 6 security and operational hardening smoke test passed."
}
finally {
    foreach ($process in $processes) {
        if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    }
    Pop-Location
}
