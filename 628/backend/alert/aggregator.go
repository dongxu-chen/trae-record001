package alert

import (
	"crypto/sha256"
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"

	"anomaly-detector/model"
)

type Aggregator struct {
	config    model.AlertConfig
	alerts    map[string]*model.Alert
	mu        sync.RWMutex
	suppressor *Suppressor
}

func NewAggregator(config model.AlertConfig) *Aggregator {
	return &Aggregator{
		config:     config,
		alerts:     make(map[string]*model.Alert),
		suppressor: NewSuppressor(config.SuppressionWindow),
	}
}

func (a *Aggregator) Aggregate(clusters []model.ClusterResult) []model.Alert {
	a.mu.Lock()
	defer a.mu.Unlock()

	var newAlerts []model.Alert

	for _, cluster := range clusters {
		if cluster.Size == 0 {
			continue
		}

		groupKey := a.computeGroupKey(cluster.Anomalies)

		if existing, ok := a.alerts[groupKey]; ok {
			if time.Since(existing.UpdatedAt) < a.config.GroupInterval {
				a.suppressor.Suppress(existing)
				continue
			}

			existing.Anomalies = mergeAnomalies(existing.Anomalies, cluster.Anomalies)
			existing.UpdatedAt = time.Now()
			if cluster.Severity != "" {
				existing.Severity = maxSeverity(existing.Severity, cluster.Severity)
			}
			existing.Description = a.buildDescription(existing.Anomalies)
			a.suppressor.Suppress(existing)
			continue
		}

		alert := model.Alert{
			ID:          fmt.Sprintf("alert-%x", sha256.Sum256([]byte(groupKey+time.Now().String())))[0:16],
			Anomalies:   cluster.Anomalies,
			Severity:    cluster.Severity,
			Title:       a.buildTitle(cluster),
			Description: a.buildDescription(cluster.Anomalies),
			CreatedAt:   time.Now(),
			UpdatedAt:   time.Now(),
			GroupKey:    groupKey,
			Suppressed:  false,
		}

		a.alerts[groupKey] = &alert
		newAlerts = append(newAlerts, alert)
	}

	return newAlerts
}

func (a *Aggregator) computeGroupKey(anomalies []model.Anomaly) string {
	metrics := make([]string, 0, len(anomalies))
	metricSet := make(map[string]bool)
	for _, anom := range anomalies {
		if !metricSet[anom.Metric] {
			metricSet[anom.Metric] = true
			metrics = append(metrics, anom.Metric)
		}
	}
	sort.Strings(metrics)

	timeBucket := anomalies[0].Timestamp.Truncate(a.config.GroupWait).Unix()
	return fmt.Sprintf("%s-%d", strings.Join(metrics, "|"), timeBucket)
}

func (a *Aggregator) buildTitle(cluster model.ClusterResult) string {
	metrics := make(map[string]bool)
	for _, anom := range cluster.Anomalies {
		metrics[anom.Metric] = true
	}

	metricList := make([]string, 0, len(metrics))
	for m := range metrics {
		metricList = append(metricList, m)
	}
	sort.Strings(metricList)

	direction := "异常"
	if len(cluster.Anomalies) > 0 {
		if cluster.Anomalies[0].Direction == model.DirectionUp {
			direction = "突增"
		} else if cluster.Anomalies[0].Direction == model.DirectionDown {
			direction = "突降"
		}
	}

	return fmt.Sprintf("[%s] %d个指标%s", string(cluster.Severity), len(metrics), direction)
}

func (a *Aggregator) buildDescription(anomalies []model.Anomaly) string {
	var sb strings.Builder
	for _, anom := range anomalies {
		sb.WriteString(fmt.Sprintf("- %s: 值=%.2f, 预期=%.2f, 偏差=%.2f, 方向=%s\n",
			anom.Metric, anom.Value, anom.Expected, anom.Deviation, anom.Direction))
	}
	return sb.String()
}

func (a *Aggregator) GetAlerts() []model.Alert {
	a.mu.RLock()
	defer a.mu.RUnlock()

	alerts := make([]model.Alert, 0, len(a.alerts))
	for _, alert := range a.alerts {
		alerts = append(alerts, *alert)
	}

	sort.Slice(alerts, func(i, j int) bool {
		if alerts[i].Severity != alerts[j].Severity {
			return severityOrder(alerts[i].Severity) > severityOrder(alerts[j].Severity)
		}
		return alerts[i].UpdatedAt.After(alerts[j].UpdatedAt)
	})

	return alerts
}

func (a *Aggregator) AcknowledgeAlert(alertID string) bool {
	a.mu.Lock()
	defer a.mu.Unlock()

	for _, alert := range a.alerts {
		if alert.ID == alertID {
			alert.Acknowledged = true
			return true
		}
	}
	return false
}

func mergeAnomalies(existing, newAnomalies []model.Anomaly) []model.Anomaly {
	seen := make(map[string]bool)
	for _, a := range existing {
		seen[a.ID] = true
	}

	for _, a := range newAnomalies {
		if !seen[a.ID] {
			existing = append(existing, a)
			seen[a.ID] = true
		}
	}

	return existing
}

func maxSeverity(a, b model.AlertSeverity) model.AlertSeverity {
	if severityOrder(a) > severityOrder(b) {
		return a
	}
	return b
}

func severityOrder(s model.AlertSeverity) int {
	switch s {
	case model.SeverityCritical:
		return 3
	case model.SeverityWarning:
		return 2
	case model.SeverityInfo:
		return 1
	default:
		return 0
	}
}
