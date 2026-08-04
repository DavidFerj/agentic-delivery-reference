[CmdletBinding()]
param([switch] $SkipBuild)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$completed = $false

Push-Location $projectRoot
try {
    docker compose config --quiet
    if (-not $SkipBuild) {
        docker compose build
        docker compose --profile tools build evaluator
    }
    docker compose up -d --wait

    $apiHealth = Invoke-RestMethod -Uri "http://127.0.0.1:8080/health"
    $apiBoundary = Invoke-WebRequest -Uri "http://127.0.0.1:8080/health" `
        -UseBasicParsing -Headers @{ "X-Correlation-ID" = "container-health-boundary" }
    $apiReady = Invoke-RestMethod -Uri "http://127.0.0.1:8080/ready"
    $workerHealth = Invoke-RestMethod -Uri "http://127.0.0.1:8081/health"
    $webStatus = (Invoke-WebRequest -Uri "http://127.0.0.1:3000" -UseBasicParsing).StatusCode
    if ($apiHealth.status -ne "ok" -or $apiReady.status -ne "ready" -or `
        $workerHealth.status -ne "ok" -or $webStatus -ne 200) {
        throw "One or more container health assertions failed."
    }
    if ($apiBoundary.Headers["X-Correlation-ID"] -ne "container-health-boundary" -or `
        $apiBoundary.Headers["X-Content-Type-Options"] -ne "nosniff") {
        throw "Containerized correlation or security headers are incomplete."
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
        -Method Post -Headers @{
            Authorization = "Bearer local-requester-token"
            "Idempotency-Key" = "container-health-create"
            "X-Correlation-ID" = "container-health-flow"
        } -ContentType "application/json" -Body $body
    $planned = Invoke-RestMethod -Uri (
        "http://127.0.0.1:8080/v1/workflows/{0}/plan" -f $created.workflowId
    ) -Method Post -Headers @{
        Authorization = "Bearer local-requester-token"
        "Idempotency-Key" = "container-health-plan"
        "X-Correlation-ID" = "container-health-flow"
    }
    $approved = Invoke-RestMethod -Uri (
        "http://127.0.0.1:8080/v1/workflows/{0}/approval" -f $created.workflowId
    ) -Method Post -Headers @{
        Authorization = "Bearer local-reviewer-token"
        "Idempotency-Key" = "container-health-approval"
        "X-Correlation-ID" = "container-health-flow"
    } -ContentType "application/json" -Body (@{
        decision = "approved"
        reason = "Approved by the container smoke test."
    } | ConvertTo-Json)
    $completed = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/local/tasks/process-next" `
        -Method Post -Headers @{
            Authorization = "Bearer local-operator-token"
            "Idempotency-Key" = "container-health-process"
            "X-Correlation-ID" = "container-health-flow"
        }

    if ($created.governanceDecisions[0].outcome -ne "permit_with_controls") {
        throw "Containerized sensitive intake did not receive the expected controls."
    }
    if ($planned.status -ne "awaiting_approval" -or $planned.governanceDecisions.Count -ne 2) {
        throw "Containerized planning did not preserve both governance decisions."
    }
    if (-not $planned.evaluation.passed -or $planned.evaluation.score -ne 1 -or `
        $planned.citations.Count -lt 1) {
        throw "Containerized RAG and evaluation evidence is incomplete."
    }
    if ($approved.status -ne "approved" -or $completed.status -ne "completed") {
        throw "Containerized approval and task execution did not complete."
    }
    if (-not $completed.executionResult.simulated -or $completed.governanceDecisions.Count -ne 3) {
        throw "Containerized execution evidence is incomplete."
    }

    $metrics = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/operations/metrics" `
        -Headers @{
            Authorization = "Bearer local-operator-token"
            "X-Correlation-ID" = "container-metrics"
        }
    $audit = Invoke-RestMethod -Uri "http://127.0.0.1:8080/v1/operations/audit-events?limit=5" `
        -Headers @{
            Authorization = "Bearer local-administrator-token"
            "X-Correlation-ID" = "container-audit"
        }
    if ($metrics.totalRequests -lt 5 -or $audit.events[-1].action -ne "operations.audit.read") {
        throw "Containerized operational evidence is incomplete."
    }

    docker compose --profile tools run --rm evaluator
    if ($LASTEXITCODE -ne 0) { throw "The containerized evaluator failed." }

    $completed = $true
    "Containerized web, API, worker, evaluator, and governed workflow smoke test passed."
}
finally {
    docker compose --profile tools down
    Pop-Location
}

if (-not $completed) { exit 1 }
