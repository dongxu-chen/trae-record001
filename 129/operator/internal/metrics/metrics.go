package metrics

import (
	"github.com/prometheus/client_golang/prometheus"
	"sigs.k8s.io/controller-runtime/pkg/metrics"
)

// HealthCheckMetrics holds all Prometheus metrics for the health checker
type HealthCheckMetrics struct {
	UnhealthyPods       *prometheus.GaugeVec
	UnhealthyNodes      *prometheus.GaugeVec
	ContainersRestarted *prometheus.GaugeVec
	NodesDrained        *prometheus.GaugeVec
	CheckDuration       *prometheus.HistogramVec
	ImageSecurityIssues *prometheus.GaugeVec
	QuotaRecommendations *prometheus.GaugeVec
}

// NewHealthCheckMetrics creates and registers all metrics
func NewHealthCheckMetrics() *HealthCheckMetrics {
	m := &HealthCheckMetrics{
		UnhealthyPods: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "healthcheck_unhealthy_pods_total",
				Help: "Number of unhealthy pods detected",
			},
			[]string{"namespace", "healthcheck_name"},
		),
		UnhealthyNodes: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "healthcheck_unhealthy_nodes_total",
				Help: "Number of unhealthy nodes detected",
			},
			[]string{"namespace", "healthcheck_name"},
		),
		ContainersRestarted: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "healthcheck_containers_restarted_total",
				Help: "Number of containers restarted by remediation",
			},
			[]string{"namespace", "healthcheck_name"},
		),
		NodesDrained: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "healthcheck_nodes_drained_total",
				Help: "Number of nodes drained by remediation",
			},
			[]string{"namespace", "healthcheck_name"},
		),
		CheckDuration: prometheus.NewHistogramVec(
			prometheus.HistogramOpts{
				Name:    "healthcheck_duration_seconds",
				Help:    "Duration of health check runs",
				Buckets: prometheus.DefBuckets,
			},
			[]string{"namespace", "healthcheck_name"},
		),
		ImageSecurityIssues: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "healthcheck_image_security_issues_total",
				Help: "Number of image security issues found",
			},
			[]string{"namespace", "healthcheck_name", "severity"},
		),
		QuotaRecommendations: prometheus.NewGaugeVec(
			prometheus.GaugeOpts{
				Name: "healthcheck_quota_recommendations_total",
				Help: "Number of resource quota recommendations made",
			},
			[]string{"namespace", "healthcheck_name", "resource_type"},
		),
	}

	// Register all metrics with the controller-runtime metrics registry
	metrics.Registry.MustRegister(
		m.UnhealthyPods,
		m.UnhealthyNodes,
		m.ContainersRestarted,
		m.NodesDrained,
		m.CheckDuration,
		m.ImageSecurityIssues,
		m.QuotaRecommendations,
	)

	return m
}
