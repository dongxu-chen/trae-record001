package enhancements

import (
	"time"

	"github.com/prometheus/prometheus/model/labels"
)

type Cluster struct {
	Name       string            `json:"name" yaml:"name"`
	Endpoint   string            `json:"endpoint" yaml:"endpoint"`
	Labels     map[string]string `json:"labels,omitempty" yaml:"labels,omitempty"`
	Enabled    bool              `json:"enabled" yaml:"enabled"`
	MetricPath string            `json:"metric_path,omitempty" yaml:"metric_path,omitempty"`
}

type ThanosManager struct {
	clusters       map[string]Cluster
	aggregateLabel string
}

func NewThanosManager() *ThanosManager {
	return &ThanosManager{
		clusters:       make(map[string]Cluster),
		aggregateLabel: "cluster",
	}
}

func (tm *ThanosManager) AddCluster(c Cluster) {
	tm.clusters[c.Name] = c
}

func (tm *ThanosManager) AddClusters(clusters []Cluster) {
	for _, c := range clusters {
		tm.clusters[c.Name] = c
	}
}

func (tm *ThanosManager) GetCluster(name string) (Cluster, bool) {
	c, ok := tm.clusters[name]
	return c, ok
}

func (tm *ThanosManager) GetAllClusters() []Cluster {
	var clusters []Cluster
	for _, c := range tm.clusters {
		clusters = append(clusters, c)
	}
	return clusters
}

func (tm *ThanosManager) GetEnabledClusters() []Cluster {
	var clusters []Cluster
	for _, c := range tm.clusters {
		if c.Enabled {
			clusters = append(clusters, c)
		}
	}
	return clusters
}

func (tm *ThanosManager) SetAggregateLabel(label string) {
	tm.aggregateLabel = label
}

type MultiClusterMetric struct {
	MetricName string
	Clusters   map[string]float64
	Total      float64
	Average    float64
	Max        float64
	Min        float64
}

func (tm *ThanosManager) AggregateMetrics(metrics map[string]map[string]float64) map[string]MultiClusterMetric {
	result := make(map[string]MultiClusterMetric)

	for metricName, clusterValues := range metrics {
		mcm := MultiClusterMetric{
			MetricName: metricName,
			Clusters:   make(map[string]float64),
		}

		var total, max, min float64
		count := 0
		first := true

		for clusterName, value := range clusterValues {
			if _, exists := tm.clusters[clusterName]; !exists {
				continue
			}

			mcm.Clusters[clusterName] = value
			total += value

			if first {
				max = value
				min = value
				first = false
			} else {
				if value > max {
					max = value
				}
				if value < min {
					min = value
				}
			}
			count++
		}

		mcm.Total = total
		if count > 0 {
			mcm.Average = total / float64(count)
		}
		mcm.Max = max
		mcm.Min = min

		result[metricName] = mcm
	}

	return result
}

func GenerateClusterMetricName(baseName, cluster string) string {
	return baseName + "{cluster=\"" + cluster + "\"}"
}

func (tm *ThanosManager) AddClusterLabel(originalLabels labels.Labels, clusterName string) labels.Labels {
	result := make(labels.Labels, len(originalLabels)+1)
	copy(result, originalLabels)
	result = append(result, labels.Label{
		Name:  tm.aggregateLabel,
		Value: clusterName,
	})
	return result
}

func CreateProductionClusters() []Cluster {
	return []Cluster{
		{
			Name:     "us-east-1",
			Endpoint: "http://thanos-query.us-east-1.example.com:9090",
			Labels: map[string]string{
				"region":  "us-east-1",
				"env":     "production",
				"cloud":   "aws",
			},
			Enabled: true,
		},
		{
			Name:     "us-west-2",
			Endpoint: "http://thanos-query.us-west-2.example.com:9090",
			Labels: map[string]string{
				"region":  "us-west-2",
				"env":     "production",
				"cloud":   "aws",
			},
			Enabled: true,
		},
		{
			Name:     "eu-central-1",
			Endpoint: "http://thanos-query.eu-central-1.example.com:9090",
			Labels: map[string]string{
				"region":  "eu-central-1",
				"env":     "production",
				"cloud":   "aws",
			},
			Enabled: true,
		},
		{
			Name:     "ap-southeast-1",
			Endpoint: "http://thanos-query.ap-southeast-1.example.com:9090",
			Labels: map[string]string{
				"region":  "ap-southeast-1",
				"env":     "production",
				"cloud":   "aws",
			},
			Enabled: true,
		},
	}
}

func CreateStagingClusters() []Cluster {
	return []Cluster{
		{
			Name:     "staging-us-east-1",
			Endpoint: "http://thanos-query.staging-us-east-1.example.com:9090",
			Labels: map[string]string{
				"region":  "us-east-1",
				"env":     "staging",
				"cloud":   "aws",
			},
			Enabled: true,
		},
		{
			Name:     "staging-eu-west-1",
			Endpoint: "http://thanos-query.staging-eu-west-1.example.com:9090",
			Labels: map[string]string{
				"region":  "eu-west-1",
				"env":     "staging",
				"cloud":   "aws",
			},
			Enabled: true,
		},
	}
}

type ThanosRule struct {
	Record        string            `json:"record,omitempty" yaml:"record,omitempty"`
	Alert         string            `json:"alert,omitempty" yaml:"alert,omitempty"`
	Expr          string            `json:"expr" yaml:"expr"`
	For           string            `json:"for,omitempty" yaml:"for,omitempty"`
	Labels        map[string]string `json:"labels,omitempty" yaml:"labels,omitempty"`
	Annotations   map[string]string `json:"annotations,omitempty" yaml:"annotations,omitempty"`
}

type ThanosRuleGroup struct {
	Name     string       `json:"name" yaml:"name"`
	Interval string       `json:"interval,omitempty" yaml:"interval,omitempty"`
	Rules    []ThanosRule `json:"rules" yaml:"rules"`
}

type ThanosRuleFile struct {
	Groups []ThanosRuleGroup `json:"groups" yaml:"groups"`
}

func GenerateCrossClusterAlert(alertName, expr string, severity string) ThanosRule {
	return ThanosRule{
		Alert: alertName,
		Expr:  expr,
		For:   "5m",
		Labels: map[string]string{
			"severity": severity,
			"type":     "cross-cluster",
		},
		Annotations: map[string]string{
			"summary":     "Cross cluster alert: " + alertName,
			"description": "Multi cluster alert firing on {{ $labels.cluster }}",
		},
	}
}

func GenerateClusterAvailabilityRule() ThanosRule {
	return ThanosRule{
		Record: "cluster:up:ratio",
		Expr:   "sum by (cluster) (up) / count by (cluster) (up)",
		Labels: map[string]string{
			"type": "aggregated",
		},
	}
}

func GenerateClusterErrorRateRule() ThanosRule {
	return ThanosRule{
		Record: "cluster:http_errors:rate5m",
		Expr:   "sum by (cluster) (rate(http_requests_total{status=~\"5..\"}[5m]))",
		Labels: map[string]string{
			"type": "aggregated",
		},
	}
}

func CompareClusterMetrics(current map[string]float64, baseline map[string]float64, threshold float64) map[string]float64 {
	diffs := make(map[string]float64)
	for cluster, value := range current {
		if base, ok := baseline[cluster]; ok {
			diff := (value - base) / base
			if diff > threshold {
				diffs[cluster] = diff
			}
		}
	}
	return diffs
}

func (tm *ThanosManager) EvaluateClusterHealth(metrics map[string]float64) map[string]string {
	health := make(map[string]string)

	for clusterName, upValue := range metrics {
		if upValue == 1 {
			health[clusterName] = "healthy"
		} else if upValue >= 0.5 {
			health[clusterName] = "degraded"
		} else {
			health[clusterName] = "unhealthy"
		}
	}

	return health
}
