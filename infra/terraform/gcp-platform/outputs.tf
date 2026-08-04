output "activation_enabled" {
  description = "Whether this configuration was explicitly allowed to create resources."
  value       = var.allow_resource_creation
}

output "api_url" {
  description = "API URL after explicit activation; null during plan-only validation."
  value       = local.active ? google_cloud_run_v2_service.api[0].uri : null
}

output "web_url" {
  description = "Web URL after explicit activation; null during plan-only validation."
  value       = local.active ? google_cloud_run_v2_service.web[0].uri : null
}

output "worker_url" {
  description = "Private worker URL after explicit activation; null during plan-only validation."
  value       = local.active ? google_cloud_run_v2_service.worker[0].uri : null
  sensitive   = true
}

output "workload_identity_provider" {
  description = "GitHub OIDC provider name after explicit activation."
  value       = local.active ? google_iam_workload_identity_pool_provider.github[0].name : null
}

output "deployer_service_account" {
  description = "Keyless deployment service identity after explicit activation."
  value       = local.active ? google_service_account.runtime["deployer"].email : null
}
