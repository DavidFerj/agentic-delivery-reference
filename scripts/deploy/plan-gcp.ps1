[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("development", "staging")]
    [string]$Environment,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[a-z][a-z0-9-]{4,28}[a-z0-9]$")]
    [string]$ProjectId,

    [switch]$ExecutePlan
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$terraformRoot = Join-Path $projectRoot "infra\terraform\gcp-platform"
$arguments = @(
    "-chdir=$terraformRoot",
    "plan",
    "-refresh=false",
    "-lock=false",
    "-input=false",
    "-var=environment=$Environment",
    "-var=project_id=$ProjectId",
    "-var=allow_resource_creation=false",
    "-var=runtime_adapters_ready=false"
)

if (-not $ExecutePlan) {
    Write-Host "PLAN-ONLY PREVIEW: terraform $($arguments -join ' ')"
    Write-Host "No command was executed and allow_resource_creation remains false."
    exit 0
}

$terraform = Get-Command terraform -ErrorAction SilentlyContinue
if ($null -eq $terraform) { throw "Terraform is required for -ExecutePlan." }

& $terraform.Source -chdir=$terraformRoot init -backend=false -input=false
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $terraform.Source @arguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
