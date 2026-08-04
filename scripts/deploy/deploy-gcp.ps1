[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("development", "staging", "production")]
    [string]$Environment,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[a-z][a-z0-9-]{4,28}[a-z0-9]$")]
    [string]$ProjectId,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[0-9]{12}$")]
    [string]$ProjectNumber,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")]
    [string]$GitHubRepository,

    [Parameter(Mandatory = $true)]
    [string]$BackendConfig,

    [Parameter(Mandatory = $true)]
    [string]$VarFile,

    [Parameter(Mandatory = $true)]
    [string]$Confirmation
)

$ErrorActionPreference = "Stop"
if ($Environment -eq "production") {
    throw "Production deployment is outside Phase 7 and is always rejected."
}
if ($env:ADR_ALLOW_GCP_MUTATION -ne "true") {
    throw "Set ADR_ALLOW_GCP_MUTATION=true only inside an explicitly authorized deployment session."
}
if ($Confirmation -ne "DEPLOY-$Environment") {
    throw "Confirmation must exactly match DEPLOY-$Environment."
}

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$terraformRoot = Join-Path $projectRoot "infra\terraform\gcp-platform"
$resolvedBackend = (Resolve-Path -LiteralPath $BackendConfig).Path
$resolvedVarFile = (Resolve-Path -LiteralPath $VarFile).Path
$backendTemplate = Join-Path $terraformRoot "backend.gcs.tf.example"
$backendDefinition = Join-Path $terraformRoot "backend.tf"
$planFile = Join-Path ([System.IO.Path]::GetTempPath()) "agentic-$Environment.tfplan"
$terraform = Get-Command terraform -ErrorAction SilentlyContinue
if ($null -eq $terraform) { throw "Terraform is required for deployment." }

Copy-Item -LiteralPath $backendTemplate -Destination $backendDefinition -Force
& $terraform.Source -chdir=$terraformRoot init -input=false "-backend-config=$resolvedBackend"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $terraform.Source -chdir=$terraformRoot plan -input=false -refresh=false "-var-file=$resolvedVarFile" `
    "-var=project_id=$ProjectId" "-var=project_number=$ProjectNumber" `
    "-var=github_repository=$GitHubRepository" "-var=environment=$Environment" `
    -var=runtime_adapters_ready=true -var=allow_resource_creation=true -out=$planFile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
terraform -chdir=$terraformRoot apply -input=false $planFile
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
