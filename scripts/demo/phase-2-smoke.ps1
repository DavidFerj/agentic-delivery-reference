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

    $headers = @{
        Authorization = "Bearer local-requester-token"
        "Idempotency-Key" = "phase-2-smoke"
        "X-Correlation-ID" = "phase-2-smoke"
    }
    $body = @{ request = "Prepare a smoke-tested delivery proposal"; requestedLocale = "en" } |
        ConvertTo-Json
    $created = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/service-requests" `
        -Method Post -Headers $headers -ContentType "application/json" -Body $body
    $fetched = Invoke-RestMethod -Uri (
        "http://127.0.0.1:8080/v1/workflows/{0}" -f $created.workflowId
    ) -Headers @{ Authorization = "Bearer local-requester-token" }

    if ($created.status -ne "received" -or $fetched.workflowId -ne $created.workflowId) {
        throw "Authenticated workflow journey returned unexpected data."
    }

    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8080/v1/session" -UseBasicParsing -TimeoutSec 2
        throw "Anonymous protected request was unexpectedly allowed."
    }
    catch {
        if ($_.Exception.Response.StatusCode.value__ -ne 401) { throw }
    }

    "Phase 2 authenticated vertical-slice smoke test passed."
}
finally {
    foreach ($process in $processes) {
        if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
    }
    Pop-Location
}
