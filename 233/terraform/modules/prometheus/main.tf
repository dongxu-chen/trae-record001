variable "region" {
  description = "Cloud region"
  type        = string
}

variable "providers" {
  description = "Cloud provider"
  type        = string
}

resource "local_file" "prometheus_config" {
  filename = "${path.module}/prometheus.yml"
  content  = <<-EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['localhost:9100']
    ec2_sd_configs:
      - region: ${var.region}
        port: 9100
    relabel_configs:
      - source_labels: [__meta_ec2_tag_Name]
        regex: autoscaler.*
        action: keep
EOF
}

resource "local_file" "prometheus_rules" {
  filename = "${path.module}/rules.yml"
  content  = <<-EOF
groups:
  - name: autoscaler
    rules:
      - record: instance:cpu_utilization:avg
        expr: avg(100 - (rate(node_cpu_seconds_total{mode="idle"}[5m]) * 100))
      - record: instance:memory_utilization:avg
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
EOF
}

output "config_file" {
  value = local_file.prometheus_config.filename
}

output "rules_file" {
  value = local_file.prometheus_rules.filename
}
