[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$pytest = Join-Path $projectRoot ".venv\Scripts\pytest.exe"

& $pytest (Join-Path $projectRoot "services\api\tests\test_cloud_config.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $python (Join-Path $projectRoot "scripts\infra\validate_gcp_readiness.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$preview = & powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File (Join-Path $projectRoot "scripts\deploy\plan-gcp.ps1") `
    -Environment development -ProjectId agentic-dev-12345
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (($preview -join "`n") -notmatch "No command was executed") {
    throw "The plan preview did not prove its non-executing default."
}

$ErrorActionPreference = "Continue"
& powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File (Join-Path $projectRoot "scripts\deploy\deploy-gcp.ps1") `
    -Environment production -ProjectId agentic-prod-12345 -ProjectNumber 123456789012 `
    -GitHubRepository example/agentic-delivery-reference -BackendConfig missing `
    -VarFile missing -Confirmation DEPLOY-production 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    throw "The deployment script did not reject production."
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File (Join-Path $projectRoot "scripts\deploy\deploy-gcp.ps1") `
    -Environment development -ProjectId agentic-dev-12345 -ProjectNumber 123456789012 `
    -GitHubRepository example/agentic-delivery-reference -BackendConfig missing `
    -VarFile missing -Confirmation DEPLOY-development 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    throw "The deployment script did not require the local mutation environment gate."
}
$ErrorActionPreference = "Stop"

Write-Host "Phase 7 plan-only Google Cloud deployment readiness smoke test passed."
