[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$venvBin = Join-Path $projectRoot ".venv\Scripts"
$python = Join-Path $venvBin "python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Local environment missing. Run scripts/setup/bootstrap.ps1 first."
}

Push-Location $projectRoot
try {
    & (Join-Path $venvBin "ruff.exe") format --check services packages/governance-core scripts
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & (Join-Path $venvBin "ruff.exe") check services packages/governance-core scripts
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & (Join-Path $venvBin "mypy.exe")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & (Join-Path $venvBin "pytest.exe") --cov --cov-report=term-missing
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & (Join-Path $venvBin "agentic-evaluator.exe")
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & (Join-Path $venvBin "pytest.exe") services/api/tests/test_security_hardening.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python scripts/quality/validate_repository.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $python scripts/infra/validate_gcp_readiness.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    pnpm.cmd check:web
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
