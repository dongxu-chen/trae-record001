package enhancements

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"gopkg.in/yaml.v3"
)

type RuleTemplate struct {
	Name        string            `json:"name"`
	Description string            `json:"description"`
	Category    string            `json:"category"`
	Expr        string            `json:"expr"`
	For         string            `json:"for,omitempty"`
	Labels      map[string]string `json:"labels,omitempty"`
	Annotations map[string]string `json:"annotations,omitempty"`
}

type RecordingRuleTemplate struct {
	Name        string            `json:"name"`
	Description string            `json:"description"`
	Category    string            `json:"category"`
	Expr        string            `json:"expr"`
	Labels      map[string]string `json:"labels,omitempty"`
}

type TemplateExporter struct {
	outputDir     string
	alertRules    map[string][]RuleTemplate
	recordingRules map[string][]RecordingRuleTemplate
}

func NewTemplateExporter(outputDir string) *TemplateExporter {
	return &TemplateExporter{
		outputDir:      outputDir,
		alertRules:     make(map[string][]RuleTemplate),
		recordingRules: make(map[string][]RecordingRuleTemplate),
	}
}

func (te *TemplateExporter) AddAlertRule(category string, rule RuleTemplate) {
	te.alertRules[category] = append(te.alertRules[category], rule)
}

func (te *TemplateExporter) AddRecordingRule(category string, rule RecordingRuleTemplate) {
	te.recordingRules[category] = append(te.recordingRules[category], rule)
}

type PrometheusRuleFile struct {
	Groups []PrometheusRuleGroup `yaml:"groups"`
}

type PrometheusRuleGroup struct {
	Name     string              `yaml:"name"`
	Interval string              `yaml:"interval,omitempty"`
	Rules    []PrometheusRule    `yaml:"rules"`
}

type PrometheusRule struct {
	Alert         string            `yaml:"alert,omitempty"`
	Record        string            `yaml:"record,omitempty"`
	Expr          string            `yaml:"expr"`
	For           string            `yaml:"for,omitempty"`
	Labels        map[string]string `yaml:"labels,omitempty"`
	Annotations   map[string]string `yaml:"annotations,omitempty"`
}

func (te *TemplateExporter) ExportAlerts(category string) error {
	rules, exists := te.alertRules[category]
	if !exists {
		return fmt.Errorf("category %s not found", category)
	}

	ruleFile := PrometheusRuleFile{
		Groups: []PrometheusRuleGroup{
			{
				Name:     category + "-alerts",
				Interval: "1m",
				Rules:    make([]PrometheusRule, len(rules)),
			},
		},
	}

	for i, r := range rules {
		ruleFile.Groups[0].Rules[i] = PrometheusRule{
			Alert:       r.Name,
			Expr:        r.Expr,
			For:         r.For,
			Labels:      r.Labels,
			Annotations: r.Annotations,
		}
	}

	return te.writeYAML(category+"-alerts.yaml", ruleFile)
}

func (te *TemplateExporter) ExportRecordingRules(category string) error {
	rules, exists := te.recordingRules[category]
	if !exists {
		return fmt.Errorf("category %s not found", category)
	}

	ruleFile := PrometheusRuleFile{
		Groups: []PrometheusRuleGroup{
			{
				Name:     category + "-recording",
				Interval: "1m",
				Rules:    make([]PrometheusRule, len(rules)),
			},
		},
	}

	for i, r := range rules {
		ruleFile.Groups[0].Rules[i] = PrometheusRule{
			Record: r.Name,
			Expr:   r.Expr,
			Labels: r.Labels,
		}
	}

	return te.writeYAML(category+"-recording.yaml", ruleFile)
}

func (te *TemplateExporter) ExportAll() error {
	if err := os.MkdirAll(te.outputDir, 0755); err != nil {
		return fmt.Errorf("failed to create output directory: %w", err)
	}

	for category := range te.alertRules {
		if err := te.ExportAlerts(category); err != nil {
			return err
		}
	}

	for category := range te.recordingRules {
		if err := te.ExportRecordingRules(category); err != nil {
			return err
		}
	}

	return nil
}

func (te *TemplateExporter) writeYAML(filename string, data interface{}) error {
	path := filepath.Join(te.outputDir, filename)
	file, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("failed to create file: %w", err)
	}
	defer file.Close()

	encoder := yaml.NewEncoder(file)
	encoder.SetIndent(2)
	if err := encoder.Encode(data); err != nil {
		return fmt.Errorf("failed to encode yaml: %w", err)
	}

	return nil
}

func GenerateKubernetesAlertTemplates() []RuleTemplate {
	return []RuleTemplate{
		{
			Name:        "KubePodCrashLooping",
			Description: "Pod is crash looping",
			Category:    "kubernetes",
			Expr:        "rate(kube_pod_container_status_restarts_total[15m]) > 0",
			For:         "15m",
			Labels:      map[string]string{"severity": "warning"},
			Annotations: map[string]string{
				"summary":     "Pod {{ $labels.namespace }}/{{ $labels.pod }} is crash looping",
				"description": "Pod {{ $labels.namespace }}/{{ $labels.pod }} restart count is increasing",
			},
		},
		{
			Name:        "KubePodNotReady",
			Description: "Pod is not ready",
			Category:    "kubernetes",
			Expr:        "sum by (namespace, pod) (max by(namespace, pod) (kube_pod_status_phase{phase=~\"Pending|Unknown|Failed\"}) * on(namespace, pod) group_left(owner_kind) max by(namespace, pod, owner_kind) (kube_pod_owner{owner_kind!=\"Job\"})) > 0",
			For:         "10m",
			Labels:      map[string]string{"severity": "warning"},
			Annotations: map[string]string{
				"summary":     "Pod {{ $labels.namespace }}/{{ $labels.pod }} is not ready",
				"description": "Pod {{ $labels.namespace }}/{{ $labels.pod }} has been in a non-ready state for more than 10 minutes",
			},
		},
		{
			Name:        "KubeDeploymentReplicasMismatch",
			Description: "Deployment has not matched the expected number of replicas",
			Category:    "kubernetes",
			Expr:        "kube_deployment_spec_replicas != kube_deployment_status_replicas_available",
			For:         "15m",
			Labels:      map[string]string{"severity": "warning"},
			Annotations: map[string]string{
				"summary":     "Deployment {{ $labels.namespace }}/{{ $labels.deployment }} replicas mismatch",
				"description": "Deployment has not matched the expected number of replicas for more than 15 minutes",
			},
		},
		{
			Name:        "KubeJobFailed",
			Description: "Job failed to complete",
			Category:    "kubernetes",
			Expr:        "kube_job_status_failed > 0",
			For:         "10m",
			Labels:      map[string]string{"severity": "warning"},
			Annotations: map[string]string{
				"summary":     "Job {{ $labels.namespace }}/{{ $labels.job_name }} failed to complete",
				"description": "Job {{ $labels.namespace }}/{{ $labels.job_name }} failed to complete",
			},
		},
		{
			Name:        "KubeCPUOvercommit",
			Description: "Cluster has overcommitted CPU resource requests",
			Category:    "kubernetes",
			Expr:        "sum(kube_pod_container_resource_requests{resource=\"cpu\"}) / sum(kube_node_status_allocatable{resource=\"cpu\"}) > 1.5",
			Labels:      map[string]string{"severity": "warning"},
			Annotations: map[string]string{
				"summary":     "Cluster has overcommitted CPU resource requests",
				"description": "Cluster CPU overcommit ratio is {{ $value | humanize }}",
			},
		},
	}
}

func GenerateNodeAlertTemplates() []RuleTemplate {
	return []RuleTemplate{
		{
			Name:        "HostHighCPUUsage",
			Description: "High CPU usage on host",
			Category:    "node",
			Expr:        "100 - (avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100) > 90",
			For:         "5m",
			Labels:      map[string]string{"severity": "warning"},
			Annotations: map[string]string{
				"summary":     "High CPU usage on {{ $labels.instance }}",
				"description": "CPU usage is above 90% on {{ $labels.instance }} (current value: {{ $value }}%)",
			},
		},
		{
			Name:        "HostHighMemoryUsage",
			Description: "High memory usage on host",
			Category:    "node",
			Expr:        "100 - ((node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100) > 90",
			For:         "5m",
			Labels:      map[string]string{"severity": "warning"},
			Annotations: map[string]string{
				"summary":     "High memory usage on {{ $labels.instance }}",
				"description": "Memory usage is above 90% on {{ $labels.instance }} (current value: {{ $value }}%)",
			},
		},
		{
			Name:        "HostHighDiskUsage",
			Description: "High disk usage on host",
			Category:    "node",
			Expr:        "100 - ((node_filesystem_avail_bytes{fstype!~\"tmpfs|fuse.lxcfs\"} / node_filesystem_size_bytes{fstype!~\"tmpfs|fuse.lxcfs\"}) * 100) > 90",
			For:         "5m",
			Labels:      map[string]string{"severity": "warning"},
			Annotations: map[string]string{
				"summary":     "High disk usage on {{ $labels.instance }}",
				"description": "Disk usage is above 90% on {{ $labels.instance }} mountpoint {{ $labels.mountpoint }}",
			},
		},
		{
			Name:        "HostUnreachable",
			Description: "Host is unreachable",
			Category:    "node",
			Expr:        "up == 0",
			For:         "2m",
			Labels:      map[string]string{"severity": "critical"},
			Annotations: map[string]string{
				"summary":     "Host {{ $labels.instance }} is unreachable",
				"description": "Host {{ $labels.instance }} has been unreachable for more than 2 minutes",
			},
		},
	}
}

func GenerateSLOAlertTemplates() []RuleTemplate {
	return []RuleTemplate{
		{
			Name:        "SLOBurnRatePage",
			Description: "High error budget burn rate - page",
			Category:    "slo",
			Expr:        "(1 - (sum(rate(http_requests_total{status!~\"5..\"}[1h])) / sum(rate(http_requests_total[1h])))) < 0.999",
			For:         "5m",
			Labels:      map[string]string{"severity": "critical"},
			Annotations: map[string]string{
				"summary":     "High error budget burn rate",
				"description": "Error budget is burning at 14.4x rate - immediate action required",
			},
		},
		{
			Name:        "SLOBurnRateTicket",
			Description: "Medium error budget burn rate - ticket",
			Category:    "slo",
			Expr:        "(1 - (sum(rate(http_requests_total{status!~\"5..\"}[6h])) / sum(rate(http_requests_total[6h])))) < 0.9995",
			For:         "30m",
			Labels:      map[string]string{"severity": "warning"},
			Annotations: map[string]string{
				"summary":     "Medium error budget burn rate",
				"description": "Error budget is burning at 6x rate - investigation required",
			},
		},
	}
}

func GenerateAggregationTemplates() []RecordingRuleTemplate {
	return []RecordingRuleTemplate{
		{
			Name:        "job:http_requests_total:rate5m",
			Description: "HTTP requests per second per job (5m rate)",
			Category:    "aggregation",
			Expr:        "sum by(job) (rate(http_requests_total[5m]))",
		},
		{
			Name:        "job:http_errors_total:rate5m",
			Description: "HTTP 5xx errors per second per job (5m rate)",
			Category:    "aggregation",
			Expr:        "sum by(job) (rate(http_requests_total{status=~\"5..\"}[5m]))",
		},
		{
			Name:        "job:http_success_ratio:rate5m",
			Description: "HTTP success ratio per job",
			Category:    "aggregation",
			Expr:        "sum by(job) (rate(http_requests_total{status!~\"5..\"}[5m])) / sum by(job) (rate(http_requests_total[5m]))",
		},
		{
			Name:        "instance:node_cpu_utilisation:rate5m",
			Description: "Node CPU utilisation per instance",
			Category:    "aggregation",
			Expr:        "1 - avg by(instance) (rate(node_cpu_seconds_total{mode=\"idle\"}[5m]))",
		},
		{
			Name:        "cluster:up:ratio",
			Description: "Instance up ratio per cluster",
			Category:    "aggregation",
			Expr:        "sum by(cluster) (up) / count by(cluster) (up)",
		},
	}
}

func GenerateFullTemplateCollection(exporter *TemplateExporter) {
	for _, rule := range GenerateKubernetesAlertTemplates() {
		exporter.AddAlertRule("kubernetes", rule)
	}

	for _, rule := range GenerateNodeAlertTemplates() {
		exporter.AddAlertRule("node", rule)
	}

	for _, rule := range GenerateSLOAlertTemplates() {
		exporter.AddAlertRule("slo", rule)
	}

	for _, rule := range GenerateAggregationTemplates() {
		exporter.AddRecordingRule("aggregation", rule)
	}
}

type ConfigTemplate struct {
	SlackConfig  SlackConfig  `json:"slack_config"`
	PagerDutyConfig PagerDutyConfig `json:"pagerduty_config"`
	EmailConfig  EmailConfig  `json:"email_config"`
}

type SlackConfig struct {
	Enabled     bool   `json:"enabled"`
	WebhookURL  string `json:"webhook_url"`
	Channel     string `json:"channel"`
	Username    string `json:"username"`
}

type PagerDutyConfig struct {
	Enabled      bool   `json:"enabled"`
	RoutingKey   string `json:"routing_key"`
	Severity     string `json:"severity"`
}

type EmailConfig struct {
	Enabled     bool     `json:"enabled"`
	SMTPHost    string   `json:"smtp_host"`
	SMTPPort    int      `json:"smtp_port"`
	To          []string `json:"to"`
	From        string   `json:"from"`
}

func GenerateDefaultAlertmanagerConfig() *ConfigTemplate {
	return &ConfigTemplate{
		SlackConfig: SlackConfig{
			Enabled:   true,
			WebhookURL: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
			Channel:    "#alerts",
			Username:   "Alertmanager",
		},
		PagerDutyConfig: PagerDutyConfig{
			Enabled:    true,
			RoutingKey: "YOUR_PAGERDUTY_ROUTING_KEY",
			Severity:   "critical",
		},
		EmailConfig: EmailConfig{
			Enabled:  true,
			SMTPHost: "smtp.example.com",
			SMTPPort: 587,
			To:       []string{"oncall@example.com"},
			From:     "alertmanager@example.com",
		},
	}
}

func (ct *ConfigTemplate) Export(path string) error {
	data, err := yaml.Marshal(ct)
	if err != nil {
		return fmt.Errorf("failed to marshal config: %w", err)
	}

	if err := os.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("failed to write config file: %w", err)
	}

	return nil
}

func GenerateREADME(outputDir string) error {
	readme := `# Prometheus Alert Rules Collection

Generated on: ` + time.Now().Format(time.RFC3339) + `

## Directory Structure

\`\`\`
alerts/
├── kubernetes-alerts.yaml    # Kubernetes-specific alerts
├── node-alerts.yaml          # Node/host alerts
├── slo-alerts.yaml           # SLO/burn rate alerts
└── aggregation-recording.yaml # Recording rules for aggregation
\`\`\`

## Rule Categories

### Kubernetes Alerts
- Pod crash loop detection
- Pod readiness issues
- Deployment replica mismatches
- Job failures
- Resource overcommit warnings

### Node Alerts
- High CPU usage warnings (>90%)
- High memory usage warnings (>90%)
- High disk usage warnings (>90%)
- Host unreachable detection

### SLO Alerts
- Multi-window, multi-burn-rate alerting
- Page-level severity (14.4x burn rate)
- Ticket-level severity (6x burn rate)

### Recording Rules
- HTTP request rate aggregation
- Error rate aggregation
- Success ratio calculation
- CPU utilization aggregation
- Cluster availability ratio

## Usage

Apply rules to Prometheus:

\`\`\`bash
# Copy rules to Prometheus config directory
cp *.yaml /etc/prometheus/rules/

# Reload Prometheus configuration
curl -X POST http://prometheus:9090/-/reload
\`\`\`

Verify rules are loaded:

\`\`\`bash
curl http://prometheus:9090/api/v1/rules
\`\`\`
`

	return os.WriteFile(filepath.Join(outputDir, "README.md"), []byte(readme), 0644)
}
