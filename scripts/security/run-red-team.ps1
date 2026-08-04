[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$pytest = Join-Path $projectRoot ".venv\Scripts\pytest.exe"

Push-Location $projectRoot
try {
    & $pytest services/api/tests/test_security_hardening.py
    if ($LASTEXITCODE -ne 0) { throw "The deterministic red-team suite failed." }
    "Deterministic Phase 6 red-team suite passed."
}
finally {
    Pop-Location
}
