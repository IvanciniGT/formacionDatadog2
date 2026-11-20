# Minimal "Datadog as code" example for lab10. Creates copies prefixed "tf -" so it never
# collides with what people built by hand. terraform init && terraform plan; destroy after.
terraform {
  required_providers {
    datadog = {
      source  = "DataDog/datadog"
      version = "~> 3.60"
    }
  }
}

variable "dd_api_key" { sensitive = true }
variable "dd_app_key" { sensitive = true }

provider "datadog" {
  api_key = var.dd_api_key
  app_key = var.dd_app_key
  api_url = "https://api.datadoghq.eu/"
}

resource "datadog_monitor" "shop_api_latency" {
  name    = "tf - [shop] shop-api p95 latency high on {{resource_name.name}}"
  type    = "query alert"
  query   = "avg(last_5m):p95:trace.servlet.request{env:course,service:shop-api} by {resource_name} > 1"
  message = <<-EOT
    {{#is_alert}}p95 latency on {{resource_name.name}} is {{value}} s{{/is_alert}}
    {{#is_recovery}}recovered: {{value}} s{{/is_recovery}}
    Runbook: https://wiki.example.com/runbooks/shop-api-latency
  EOT
  monitor_thresholds {
    critical          = 1
    warning           = 0.7
    critical_recovery = 0.5
  }
  require_full_window = true
  notify_no_data      = false
  renotify_interval   = 30
  priority            = 3
  tags                = ["team:training", "service:shop-api", "managed-by:terraform"]
}

resource "datadog_synthetics_test" "products_api" {
  name      = "tf - shop api products"
  type      = "api"
  subtype   = "http"
  status    = "live"
  locations = ["aws:eu-central-1", "aws:eu-west-3"]
  tags      = ["team:training", "managed-by:terraform"]
  request_definition {
    method = "GET"
    url    = "https://datadog.iochannel.tech/api/products"
  }
  assertion {
    type     = "statusCode"
    operator = "is"
    target   = "200"
  }
  assertion {
    type     = "responseTime"
    operator = "lessThan"
    target   = "1000"
  }
  options_list {
    tick_every         = 300
    min_failure_duration = 60
    min_location_failed  = 2
    retry {
      count    = 1
      interval = 30000
    }
  }
  message = "Products API failing @slack-shop-alerts"
}

resource "datadog_dashboard_json" "shop_ops" {
  dashboard = file("${path.module}/shop_ops.json")   # export your lab02 dashboard JSON here (gear -> Export)
}
