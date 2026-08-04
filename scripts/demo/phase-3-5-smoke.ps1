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
    $env:ADR_GOVERNANCE_MODE = "enforce"
    $processes.Add((Start-Process -FilePath $python -ArgumentList @(
        "-m", "uvicorn", "agentic_api.main:app", "--host", "127.0.0.1", "--port", "8080"
    ) -WindowStyle Hidden -PassThru))
    $processes.Add((Start-Process -FilePath "node" -ArgumentList @(
        $next, "start", "--hostname", "127.0.0.1", "--port", "3000"
    ) -WorkingDirectory $webRoot -WindowStyle Hidden -PassThru))

    Wait-ForEndpoint -Uri "http://127.0.0.1:8080/health"
    Wait-ForEndpoint -Uri "http://127.0.0.1:3000"

    $headers = @{
        Authorization = "Bearer local-requester-token"
        "Idempotency-Key" = "phase-3-5-health-create"
        "X-Correlation-ID" = "phase-3-5-health"
    }
    $body = @{
        request = "Prepare local support for a patient symptom report"
        requestedLocale = "en"
        dataContext = @{
            declaredCategories = @("health_information")
            purpose = "delivery_planning"
            jurisdiction = "US"
            overlayIds = @("common-us-baseline")
        }
    } | ConvertTo-Json -Depth 5
    $created = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/service-requests" `
        -Method Post -Headers $headers -ContentType "application/json" -Body $body
    $planned = Invoke-RestMethod -Uri (
        "http://127.0.0.1:8080/v1/workflows/{0}/plan" -f $created.workflowId
    ) -Method Post -Headers @{
        Authorization = "Bearer local-requester-token"
        "Idempotency-Key" = "phase-3-5-health-plan"
        "X-Correlation-ID" = "phase-3-5-health"
    }

    if ($created.governanceDecisions[0].outcome -ne "permit_with_controls") {
        throw "Sensitive intake did not receive the expected policy controls."
    }
    if ($planned.governanceDecisions.Count -ne 2 -or $planned.status -ne "awaiting_approval") {
        throw "Policy was not evaluated at both processing boundaries."
    }

    $denied = $false
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/service-requests" `
            -Method Post -Headers @{
                Authorization = "Bearer local-requester-token"
                "Idempotency-Key" = "phase-3-5-denied-create"
            } -ContentType "application/json" -Body (@{
                request = "Store this API key in the workflow"
                requestedLocale = "en"
            } | ConvertTo-Json) | Out-Null
    }
    catch {
        $denied = $_.Exception.Response.StatusCode -eq 403
    }
    if (-not $denied) { throw "Prohibited intake was not denied before storage." }

    "Phase 3.5 data-protection control-plane smoke test passed."
}
finally {
    Remove-Item Env:ADR_GOVERNANCE_MODE -ErrorAction SilentlyContinue
    foreach ($process in $processes) {
        if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    }
    Pop-Location
}
