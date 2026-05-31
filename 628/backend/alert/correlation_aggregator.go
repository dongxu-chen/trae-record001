package alert

import (
	"crypto/sha256"
	"fmt"
	"math"
	"sort"
	"strings"
	"sync"
	"time"

	"anomaly-detector/model"
)

type CorrelationBasedAggregator struct {
	config             model.AlertConfig
	alerts             map[string]*model.Alert
	correlationMatrix  map[string]map[string]float64
	mu                 sync.RWMutex
	suppressor         *Suppressor
	correlationThreshold float64
}

func NewCorrelationAggregator(config model.AlertConfig, correlationThreshold float64) *CorrelationBasedAggregator {
	if correlationThreshold <= 0 {
		correlationThreshold = 0.5
	}
	return &CorrelationBasedAggregator{
		config:               config,
		alerts:               make(map[string]*model.Alert),
		correlationMatrix:    make(map[string]map[string]float64),
		suppressor:           NewSuppressor(config.SuppressionWindow),
		correlationThreshold: correlationThreshold,
	}
}

func (a *CorrelationBasedAggregator) UpdateCorrelations(metricA, metricB string, correlation float64) {
	a.mu.Lock()
	defer a.mu.Unlock()

	if a.correlationMatrix[metricA] == nil {
		a.correlationMatrix[metricA] = make(map[string]float64)
	}
	a.correlationMatrix[metricA][metricB] = correlation

	if a.correlationMatrix[metricB] == nil {
		a.correlationMatrix[metricB] = make(map[string]float64)
	}
	a.correlationMatrix[metricB][metricA] = correlation
}

func (a *CorrelationBasedAggregator) GetCorrelation(metricA, metricB string) float64 {
	a.mu.RLock()
	defer a.mu.RUnlock()

	if a.correlationMatrix[metricA] != nil {
		return a.correlationMatrix[metricA][metricB]
	}
	return 0
}

func (a *CorrelationBasedAggregator) AreCorrelated(metricA, metricB string) bool {
	return math.Abs(a.GetCorrelation(metricA, metricB)) >= a.correlationThreshold
}

func (a *CorrelationBasedAggregator) AggregateWithCorrelation(clusters []model.ClusterResult, correlations map[string]float64) []model.Alert {
	a.mu.Lock()
	defer a.mu.Unlock()

	for pair, corr := range correlations {
		parts := strings.Split(pair, "|||")
		if len(parts) == 2 {
			if a.correlationMatrix[parts[0]] == nil {
				a.correlationMatrix[parts[0]] = make(map[string]float64)
			}
			a.correlationMatrix[parts[0]][parts[1]] = corr
			if a.correlationMatrix[parts[1]] == nil {
				a.correlationMatrix[parts[1]] = make(map[string]float64)
			}
			a.correlationMatrix[parts[1]][parts[0]] = corr
		}
	}

	mergedClusters := a.mergeCorrelatedClusters(clusters)

	var newAlerts []model.Alert

	for _, cluster := range mergedClusters {
		if cluster.Size == 0 {
			continue
		}

		groupKey := a.computeCorrelationGroupKey(cluster.Anomalies)

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
			existing.Description = a.buildDescriptionWithCorrelation(existing.Anomalies)
			existing.Title = a.buildTitleWithCorrelation(cluster)
			a.suppressor.Suppress(existing)
			continue
		}

		alert := model.Alert{
			ID:          fmt.Sprintf("alert-%x", sha256.Sum256([]byte(groupKey+time.Now().String())))[0:16],
			Anomalies:   cluster.Anomalies,
			Severity:    cluster.Severity,
			Title:       a.buildTitleWithCorrelation(cluster),
			Description: a.buildDescriptionWithCorrelation(cluster.Anomalies),
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

func (a *CorrelationBasedAggregator) mergeCorrelatedClusters(clusters []model.ClusterResult) []model.ClusterResult {
	if len(clusters) <= 1 {
		return clusters
	}

	merged := make([]model.ClusterResult, 0)
	mergedIndices := make(map[int]bool)

	for i := 0; i < len(clusters); i++ {
		if mergedIndices[i] {
			continue
		}

		cluster := clusters[i]
		mergedIndices[i] = true

		for j := i + 1; j < len(clusters); j++ {
			if mergedIndices[j] {
				continue
			}

			if a.shouldMergeClusters(cluster, clusters[j]) {
				cluster = a.mergeTwoClusters(cluster, clusters[j])
				mergedIndices[j] = true
			}
		}

		merged = append(merged, cluster)
	}

	return merged
}

func (a *CorrelationBasedAggregator) shouldMergeClusters(c1, c2 model.ClusterResult) bool {
	metrics1 := a.getUniqueMetrics(c1.Anomalies)
	metrics2 := a.getUniqueMetrics(c2.Anomalies)

	for m1 := range metrics1 {
		for m2 := range metrics2 {
			if m1 == m2 {
				return true
			}
			if a.AreCorrelated(m1, m2) {
				return true
			}
		}
	}

	timeDiff := math.Abs(float64(c1.CenterTime.Sub(c2.CenterTime).Minutes()))
	if timeDiff < 10 {
		metricOverlap := 0.0
		for m1 := range metrics1 {
			for m2 := range metrics2 {
				if m1 == m2 {
					metricOverlap++
				}
			}
		}
		if metricOverlap > 0 {
			return true
		}
	}

	return false
}

func (a *CorrelationBasedAggregator) mergeTwoClusters(c1, c2 model.ClusterResult) model.ClusterResult {
	mergedAnomalies := mergeAnomalies(c1.Anomalies, c2.Anomalies)

	allMetrics := a.getUniqueMetrics(mergedAnomalies)
	totalCorrelation := 0.0
	corrCount := 0
	metricsList := make([]string, 0, len(allMetrics))
	for m := range allMetrics {
		metricsList = append(metricsList, m)
	}
	for i := 0; i < len(metricsList); i++ {
		for j := i + 1; j < len(metricsList); j++ {
			if corr := a.GetCorrelation(metricsList[i], metricsList[j]); corr != 0 {
				totalCorrelation += math.Abs(corr)
				corrCount++
			}
		}
	}

	newSeverity := maxSeverity(c1.Severity, c2.Severity)
	if corrCount > 0 && totalCorrelation/float64(corrCount) > 0.7 {
		if newSeverity == model.SeverityWarning {
			newSeverity = model.SeverityCritical
		}
	}

	return model.ClusterResult{
		ClusterID:  c1.ClusterID,
		Anomalies:  mergedAnomalies,
		CenterTime: c1.CenterTime.Add(c2.CenterTime.Sub(c1.CenterTime) / 2),
		Size:       len(mergedAnomalies),
		Severity:   newSeverity,
	}
}

func (a *CorrelationBasedAggregator) getUniqueMetrics(anomalies []model.Anomaly) map[string]bool {
	metrics := make(map[string]bool)
	for _, a := range anomalies {
		metrics[a.Metric] = true
	}
	return metrics
}

func (a *CorrelationBasedAggregator) computeCorrelationGroupKey(anomalies []model.Anomaly) string {
	metrics := make([]string, 0, len(anomalies))
	metricSet := make(map[string]bool)
	for _, anom := range anomalies {
		if !metricSet[anom.Metric] {
			metricSet[anom.Metric] = true
			metrics = append(metrics, anom.Metric)
		}
	}
	sort.Strings(metrics)

	relatedGroup := a.getCorrelationGroup(metrics)
	sort.Strings(relatedGroup)

	earliestTime := anomalies[0].Timestamp
	for _, anom := range anomalies {
		if anom.Timestamp.Before(earliestTime) {
			earliestTime = anom.Timestamp
		}
	}
	timeBucket := earliestTime.Truncate(a.config.GroupWait).Unix()

	return fmt.Sprintf("%s-%d", strings.Join(relatedGroup, "|"), timeBucket)
}

func (a *CorrelationBasedAggregator) getCorrelationGroup(metrics []string) []string {
	visited := make(map[string]bool)
	var group []string

	var dfs func(string)
	dfs = func(metric string) {
		if visited[metric] {
			return
		}
		visited[metric] = true
		group = append(group, metric)

		for other, corr := range a.correlationMatrix[metric] {
			if math.Abs(corr) >= a.correlationThreshold && !visited[other] {
				dfs(other)
			}
		}
	}

	for _, m := range metrics {
		dfs(m)
	}

	return group
}

func (a *CorrelationBasedAggregator) buildTitleWithCorrelation(cluster model.ClusterResult) string {
	metrics := make(map[string]bool)
	for _, anom := range cluster.Anomalies {
		metrics[anom.Metric] = true
	}

	metricList := make([]string, 0, len(metrics))
	for m := range metrics {
		metricList = append(metricList, m)
	}
	sort.Strings(metricList)

	relatedCount := 0
	for i := 0; i < len(metricList); i++ {
		for j := i + 1; j < len(metricList); j++ {
			if a.AreCorrelated(metricList[i], metricList[j]) {
				relatedCount++
			}
		}
	}

	direction := "异常"
	if len(cluster.Anomalies) > 0 {
		if cluster.Anomalies[0].Direction == model.DirectionUp {
			direction = "突增"
		} else if cluster.Anomalies[0].Direction == model.DirectionDown {
			direction = "突降"
		}
	}

	if relatedCount > 0 {
		return fmt.Sprintf("[%s] %d个关联指标%s", string(cluster.Severity), len(metrics), direction)
	}
	return fmt.Sprintf("[%s] %d个指标%s", string(cluster.Severity), len(metrics), direction)
}

func (a *CorrelationBasedAggregator) buildDescriptionWithCorrelation(anomalies []model.Anomaly) string {
	var sb strings.Builder

	metricGroups := make(map[string][]model.Anomaly)
	for _, anom := range anomalies {
		metricGroups[anom.Metric] = append(metricGroups[anom.Metric], anom)
	}

	metricList := make([]string, 0, len(metricGroups))
	for m := range metricGroups {
		metricList = append(metricList, m)
	}
	sort.Strings(metricList)

	for i, m := range metricList {
		groupAnomalies := metricGroups[m]
		if len(groupAnomalies) > 0 {
			first := groupAnomalies[0]
			sb.WriteString(fmt.Sprintf("- %s: %d个异常点, 方向=%s\n",
				m, len(groupAnomalies), first.Direction))

			relatedMetrics := a.getRelatedMetricsForDisplay(m, metricList)
			if len(relatedMetrics) > 0 {
				sb.WriteString(fmt.Sprintf("  关联指标: %s\n", strings.Join(relatedMetrics, ", ")))
			}

			if len(groupAnomalies) <= 3 {
				for _, anom := range groupAnomalies {
					sb.WriteString(fmt.Sprintf("    * %s: 值=%.2f, 预期=%.2f, 偏差=%.2f\n",
						anom.Timestamp.Format("15:04:05"), anom.Value, anom.Expected, anom.Deviation))
				}
			} else {
				for j := 0; j < 2; j++ {
					anom := groupAnomalies[j]
					sb.WriteString(fmt.Sprintf("    * %s: 值=%.2f, 预期=%.2f, 偏差=%.2f\n",
						anom.Timestamp.Format("15:04:05"), anom.Value, anom.Expected, anom.Deviation))
				}
				sb.WriteString(fmt.Sprintf("    * ... 还有%d个更多\n", len(groupAnomalies)-2))
			}
		}
		_ = i
	}

	return sb.String()
}

func (a *CorrelationBasedAggregator) getRelatedMetricsForDisplay(metric string, allMetrics []string) []string {
	var related []string
	for _, m := range allMetrics {
		if m != metric && a.AreCorrelated(metric, m) {
			corr := a.GetCorrelation(metric, m)
			related = append(related, fmt.Sprintf("%s(%.2f)", m, corr))
		}
	}
	return related
}

func (a *CorrelationBasedAggregator) GetAlerts() []model.Alert {
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

func (a *CorrelationBasedAggregator) AcknowledgeAlert(alertID string) bool {
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

func (a *CorrelationBasedAggregator) Aggregate(clusters []model.ClusterResult) []model.Alert {
	return a.AggregateWithCorrelation(clusters, nil)
}
