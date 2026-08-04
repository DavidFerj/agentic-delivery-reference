[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$evaluatorCommand = Join-Path $projectRoot ".venv\Scripts\agentic-evaluator.exe"
$webRoot = Join-Path $projectRoot "apps\web-console"
$next = Join-Path $webRoot "node_modules\next\dist\bin\next"
$processes = [System.Collections.Generic.List[System.Diagnostics.Process]]::new()

function Wait-ForEndpoint {
    param(
        [Parameter(Mandatory)] [string] $Uri,
        [int] $Attempts = 30
    )

    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                return
            }
        }
        catch {
            if ($attempt -eq $Attempts) {
                throw "Endpoint did not become ready: $Uri"
            }
        }
        Start-Sleep -Milliseconds 500
    }
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "Local environment missing. Run scripts/setup/bootstrap.ps1 first."
}
if (-not (Test-Path -LiteralPath $next)) {
    throw "Web dependencies missing. Run scripts/setup/bootstrap.ps1 first."
}
if (-not (Test-Path -LiteralPath $evaluatorCommand)) {
    throw "Evaluator entry point missing. Run scripts/setup/bootstrap.ps1 first."
}

Push-Location $projectRoot
try {
    $processes.Add((Start-Process -FilePath $python -ArgumentList @(
        "-m", "uvicorn", "agentic_api.main:app", "--host", "127.0.0.1", "--port", "8080"
    ) -WindowStyle Hidden -PassThru))
    $processes.Add((Start-Process -FilePath $python -ArgumentList @(
        "-m", "uvicorn", "agentic_worker.main:app", "--host", "127.0.0.1", "--port", "8081"
    ) -WindowStyle Hidden -PassThru))
    $processes.Add((Start-Process -FilePath "node" -ArgumentList @(
        $next, "start", "--hostname", "127.0.0.1", "--port", "3000"
    ) -WorkingDirectory $webRoot -WindowStyle Hidden -PassThru))

    Wait-ForEndpoint -Uri "http://127.0.0.1:8080/health"
    Wait-ForEndpoint -Uri "http://127.0.0.1:8081/health"
    Wait-ForEndpoint -Uri "http://127.0.0.1:3000"

    $api = Invoke-RestMethod -Uri "http://127.0.0.1:8080/health" -TimeoutSec 2
    $worker = Invoke-RestMethod -Uri "http://127.0.0.1:8081/health" -TimeoutSec 2
    $evaluator = & $evaluatorCommand | ConvertFrom-Json

    if ($api.service -ne "api" -or $worker.service -ne "background-worker") {
        throw "Unexpected service identity in smoke response."
    }
    if (-not $evaluator.passed -or $evaluator.goldenSetVersion -ne "deterministic-v1") {
        throw "Unexpected evaluator gate response."
    }

    "Foundation smoke test passed."
}
finally {
    foreach ($process in $processes) {
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
        }
    }
    Pop-Location
}
