[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

Push-Location $projectRoot
try {
    if (-not (Test-Path -LiteralPath $venvPython)) {
        python -m venv .venv
    }

    & $venvPython -m pip install --upgrade "pip>=25,<26.2"
    & $venvPython -m pip install --constraint requirements/development.txt -e ".[dev]"
    pnpm.cmd install --frozen-lockfile
}
finally {
    Pop-Location
}
