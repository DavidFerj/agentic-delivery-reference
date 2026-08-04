[CmdletBinding()]
param(
    [switch]$SkipTerraform
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$terraformRoot = Join-Path $projectRoot "infra\terraform\gcp-platform"
$windowsVenvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$unixVenvPython = Join-Path $projectRoot ".venv/bin/python"

if (Test-Path -LiteralPath $windowsVenvPython) {
    $python = $windowsVenvPython
}
elseif (Test-Path -LiteralPath $unixVenvPython) {
    $python = $unixVenvPython
}
else {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCommand) {
        $pythonCommand = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if ($null -eq $pythonCommand) {
        throw "Python is unavailable. Install a supported Python runtime or bootstrap the local environment."
    }
    $python = $pythonCommand.Source
}

& $python (Join-Path $PSScriptRoot "validate_gcp_readiness.py")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($SkipTerraform) {
    Write-Host "Terraform executable validation skipped explicitly; static safety validation passed."
    exit 0
}

$terraform = Get-Command terraform -ErrorAction SilentlyContinue
if ($null -eq $terraform) {
    throw "Terraform is not installed. Use -SkipTerraform only for the static local smoke test."
}

& $terraform.Source -chdir=$terraformRoot fmt -check -recursive
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $terraform.Source -chdir=$terraformRoot init -backend=false -input=false
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $terraform.Source -chdir=$terraformRoot validate
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Terraform formatting and provider schema validation passed without applying resources."
