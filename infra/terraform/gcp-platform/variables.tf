variable "project_id" {
  description = "Existing environment-specific Google Cloud project identifier."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "project_id must be a valid Google Cloud project identifier."
  }
}
variable "project_number" {
  description = "Existing numeric project identifier, required only for activation and Workload Identity Federation."
  type        = string
  default     = "000000000000"

  validation {
    condition     = can(regex("^[0-9]{12}$", var.project_number))
    error_message = "project_number must contain exactly 12 digits."
  }
}

variable "billing_account_id" {
  description = "Billing account used only when an explicitly activated budget is created."
  type        = string
  default     = ""
  sensitive   = true
}

variable "region" {
  description = "Primary deployment region."
  type        = string
  default     = "us-central1"

  validation {
    condition     = can(regex("^[a-z]+-[a-z]+[0-9]+$", var.region))
    error_message = "region must be a valid regional Google Cloud location."
  }
}

variable "environment" {
  description = "Non-production environment represented by this state."
  type        = string

  validation {
    condition     = contains(["development", "staging"], var.environment)
    error_message = "Phase 7 supports only development or staging."
  }
}

variable "github_repository" {
  description = "GitHub repository in owner/name form trusted by Workload Identity Federation."
  type        = string
  default     = "example/agentic-delivery-reference"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must use owner/name format."
  }
}

variable "web_image" {
  description = "Immutable web container image digest."
  type        = string
  default     = "us-docker.pkg.dev/example/agentic/web@sha256:0000000000000000000000000000000000000000000000000000000000000000"
}

variable "api_image" {
  description = "Immutable API container image digest."
  type        = string
  default     = "us-docker.pkg.dev/example/agentic/api@sha256:0000000000000000000000000000000000000000000000000000000000000000"
}

variable "worker_image" {
  description = "Immutable worker container image digest."
  type        = string
  default     = "us-docker.pkg.dev/example/agentic/worker@sha256:0000000000000000000000000000000000000000000000000000000000000000"
}

variable "evaluator_image" {
  description = "Immutable evaluator container image digest."
  type        = string
  default     = "us-docker.pkg.dev/example/agentic/evaluator@sha256:0000000000000000000000000000000000000000000000000000000000000000"
}

variable "allow_resource_creation" {
  description = "Explicit mutation gate. False produces an empty managed-resource graph."
  type        = bool
  default     = false
}

variable "runtime_adapters_ready" {
  description = "Acknowledges that provider adapters were separately implemented and verified."
  type        = bool
  default     = false
}

variable "monthly_budget_usd" {
  description = "Environment budget threshold created only during explicit activation."
  type        = number
  default     = 50

  validation {
    condition     = var.monthly_budget_usd > 0 && var.monthly_budget_usd <= 10000
    error_message = "monthly_budget_usd must be between 0 and 10000."
  }
}

check "activation_is_deliberate" {
  assert {
    condition = !var.allow_resource_creation || (
      var.runtime_adapters_ready &&
      var.project_number != "000000000000" &&
      var.github_repository != "example/agentic-delivery-reference"
    )
    error_message = "Activation requires verified runtime adapters, a real project number, and an explicit GitHub repository."
  }
}
