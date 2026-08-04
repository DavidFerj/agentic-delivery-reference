locals {
  active = var.allow_resource_creation
  prefix = "adr-${var.environment}"
  labels = {
    application = "agentic-delivery-reference"
    environment = var.environment
    managed_by  = "terraform"
  }
  required_services = toset([
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudtasks.googleapis.com",
    "firestore.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
  ])
  service_accounts = toset(["api", "deployer", "evaluator", "task-invoker", "web", "worker"])
  deployer_roles = toset([
    "roles/artifactregistry.writer",
    "roles/cloudtasks.admin",
    "roles/datastore.owner",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.serviceAccountUser",
    "roles/monitoring.editor",
    "roles/resourcemanager.projectIamAdmin",
    "roles/run.admin",
    "roles/secretmanager.admin",
    "roles/serviceusage.serviceUsageAdmin",
    "roles/storage.admin",
  ])
}

resource "google_project_service" "required" {
  for_each = local.active ? local.required_services : toset([])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "containers" {
  count = local.active ? 1 : 0

  project       = var.project_id
  location      = var.region
  repository_id = "agentic-containers"
  description   = "Immutable application container images"
  format        = "DOCKER"
  labels        = local.labels

  depends_on = [google_project_service.required]
}
resource "google_service_account" "runtime" {
  for_each = local.active ? local.service_accounts : toset([])

  project      = var.project_id
  account_id   = "${local.prefix}-${each.value}"
  display_name = "${local.prefix} ${each.value} identity"

  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "api_firestore" {
  count   = local.active ? 1 : 0
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.runtime["api"].email}"
}

resource "google_project_iam_member" "worker_firestore" {
  count   = local.active ? 1 : 0
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.runtime["worker"].email}"
}

resource "google_project_iam_member" "evaluator_firestore" {
  count   = local.active ? 1 : 0
  project = var.project_id
  role    = "roles/datastore.viewer"
  member  = "serviceAccount:${google_service_account.runtime["evaluator"].email}"
}

resource "google_project_iam_member" "api_tasks" {
  count   = local.active ? 1 : 0
  project = var.project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.runtime["api"].email}"
}

resource "google_project_iam_member" "deployer" {
  for_each = local.active ? local.deployer_roles : toset([])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.runtime["deployer"].email}"
}

resource "google_firestore_database" "operational" {
  count = local.active ? 1 : 0

  project                     = var.project_id
  name                        = "(default)"
  location_id                 = var.region
  type                        = "FIRESTORE_NATIVE"
  concurrency_mode            = "PESSIMISTIC"
  app_engine_integration_mode = "DISABLED"
  deletion_policy             = "ABANDON"

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket" "artifacts" {
  count = local.active ? 1 : 0

  project                     = var.project_id
  name                        = "${var.project_id}-${var.environment}-agentic-artifacts"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = local.labels

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_storage_bucket_iam_member" "api_artifacts" {
  count  = local.active ? 1 : 0
  bucket = google_storage_bucket.artifacts[0].name
  role   = "roles/storage.objectUser"
  member = "serviceAccount:${google_service_account.runtime["api"].email}"
}

resource "google_storage_bucket_iam_member" "evaluator_artifacts" {
  count  = local.active ? 1 : 0
  bucket = google_storage_bucket.artifacts[0].name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.runtime["evaluator"].email}"
}

resource "google_secret_manager_secret" "provider_credentials" {
  count = local.active ? 1 : 0

  project   = var.project_id
  secret_id = "${local.prefix}-provider-credentials"
  labels    = local.labels

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_iam_member" "api_secret_access" {
  count     = local.active ? 1 : 0
  project   = var.project_id
  secret_id = google_secret_manager_secret.provider_credentials[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime["api"].email}"
}

resource "google_cloud_tasks_queue" "execution" {
  count = local.active ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = "${local.prefix}-execution"

  rate_limits {
    max_concurrent_dispatches = 10
    max_dispatches_per_second = 5
  }

  retry_config {
    max_attempts       = 5
    max_retry_duration = "1800s"
    min_backoff        = "5s"
    max_backoff        = "300s"
    max_doublings      = 5
  }

  depends_on = [google_project_service.required]
}

resource "google_service_account_iam_member" "tasks_oidc_signer" {
  count = local.active ? 1 : 0

  service_account_id = google_service_account.runtime["task-invoker"].name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${var.project_number}@gcp-sa-cloudtasks.iam.gserviceaccount.com"
}

resource "google_cloud_run_v2_service" "api" {
  count = local.active ? 1 : 0

  project             = var.project_id
  name                = "${local.prefix}-api"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = var.environment == "staging"

  template {
    service_account                  = google_service_account.runtime["api"].email
    timeout                          = "60s"
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      image = var.api_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      env {
        name  = "ADR_ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "ADR_AUTH_MODE"
        value = "gcp_oidc"
      }
      env {
        name  = "ADR_GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "ADR_GCP_REGION"
        value = var.region
      }

      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 2
        timeout_seconds       = 2
        failure_threshold     = 10
        period_seconds        = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
      }
    }
  }

  labels     = local.labels
  depends_on = [google_project_service.required, google_firestore_database.operational]
}

resource "google_cloud_run_v2_service" "worker" {
  count = local.active ? 1 : 0

  project             = var.project_id
  name                = "${local.prefix}-worker"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_INTERNAL_ONLY"
  deletion_protection = var.environment == "staging"

  template {
    service_account                  = google_service_account.runtime["worker"].email
    timeout                          = "300s"
    max_instance_request_concurrency = 10

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      image = var.worker_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
      }
    }
  }

  labels     = local.labels
  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service" "web" {
  count = local.active ? 1 : 0

  project             = var.project_id
  name                = "${local.prefix}-web"
  location            = var.region
  ingress             = "INGRESS_TRAFFIC_ALL"
  deletion_protection = var.environment == "staging"

  template {
    service_account                  = google_service_account.runtime["web"].email
    timeout                          = "30s"
    max_instance_request_concurrency = 80

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    containers {
      image = var.web_image

      ports {
        container_port = 3000
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
  }

  labels     = local.labels
  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_job" "evaluator" {
  count = local.active ? 1 : 0

  project             = var.project_id
  name                = "${local.prefix}-evaluator"
  location            = var.region
  deletion_protection = var.environment == "staging"

  template {
    template {
      service_account = google_service_account.runtime["evaluator"].email
      timeout         = "900s"
      max_retries     = 1

      containers {
        image = var.evaluator_image

        resources {
          limits = {
            cpu    = "1"
            memory = "512Mi"
          }
        }
      }
    }
  }

  labels     = local.labels
  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service_iam_member" "public_api" {
  count = local.active ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "public_web" {
  count = local.active ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.web[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_v2_service_iam_member" "task_worker" {
  count = local.active ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.worker[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.runtime["task-invoker"].email}"
}

resource "google_iam_workload_identity_pool" "github" {
  count = local.active ? 1 : 0

  project                   = var.project_id
  workload_identity_pool_id = "${local.prefix}-github"
  display_name              = "${local.prefix} GitHub Actions"
  description               = "Keyless deployment identity restricted to one repository"

  depends_on = [google_project_service.required]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  count = local.active ? 1 : 0

  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github[0].workload_identity_pool_id
  workload_identity_pool_provider_id = "github"
  display_name                       = "GitHub OIDC"
  attribute_condition                = "assertion.repository == '${var.github_repository}'"
  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_deployer" {
  count = local.active ? 1 : 0

  service_account_id = google_service_account.runtime["deployer"].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${var.project_number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github[0].workload_identity_pool_id}/attribute.repository/${var.github_repository}"
}

resource "google_logging_metric" "api_errors" {
  count = local.active ? 1 : 0

  project = var.project_id
  name    = "${local.prefix}-api-errors"
  filter  = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${local.prefix}-api\" AND severity>=ERROR"

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }

  depends_on = [google_project_service.required]
}

resource "google_monitoring_dashboard" "operations" {
  count = local.active ? 1 : 0

  project = var.project_id
  dashboard_json = jsonencode({
    displayName = "${local.prefix} operational overview"
    mosaicLayout = {
      columns = 12
      tiles = [{
        height = 4
        width  = 12
        widget = {
          title = "Cloud Run request count"
          xyChart = {
            dataSets = [{
              plotType = "LINE"
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\""
                  aggregation = {
                    alignmentPeriod  = "60s"
                    perSeriesAligner = "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      }]
    }
  })

  depends_on = [google_project_service.required]
}

resource "google_billing_budget" "environment" {
  count = local.active && var.billing_account_id != "" ? 1 : 0

  billing_account = var.billing_account_id
  display_name    = "${local.prefix} monthly guard"

  budget_filter {
    projects = ["projects/${var.project_number}"]
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.monthly_budget_usd)
    }
  }

  threshold_rules {
    threshold_percent = 0.5
  }
  threshold_rules {
    threshold_percent = 0.9
  }
  threshold_rules {
    threshold_percent = 1.0
  }

  depends_on = [google_project_service.required]
}
