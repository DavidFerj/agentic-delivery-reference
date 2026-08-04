[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$evaluator = Join-Path $projectRoot ".venv\Scripts\agentic-evaluator.exe"

Push-Location $projectRoot
try {
    & $evaluator
    if ($LASTEXITCODE -ne 0) { throw "The deterministic golden-set gate failed." }
}
finally {
    Pop-Location
}
