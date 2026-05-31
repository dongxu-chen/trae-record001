package clustering

import (
	"math"
	"sort"
	"time"

	"anomaly-detector/alignment"
	"anomaly-detector/model"
)

type CorrelationClusterer struct {
	timeEpsilon     time.Duration
	correlationThreshold float64
	minClusterSize  int
}

func NewCorrelationClusterer(timeEpsilon time.Duration, correlationThreshold float64, minClusterSize int) *CorrelationClusterer {
	if timeEpsilon <= 0 {
		timeEpsilon = 5 * time.Minute
	}
	if correlationThreshold <= 0 {
		correlationThreshold = 0.5
	}
	if minClusterSize <= 0 {
		minClusterSize = 1
	}
	return &CorrelationClusterer{
		timeEpsilon:          timeEpsilon,
		correlationThreshold: correlationThreshold,
		minClusterSize:       minClusterSize,
	}
}

type anomalyWithSeries struct {
	anomaly   model.Anomaly
	seriesData []float64
	metricName string
}

func (c *CorrelationClusterer) ClusterWithSeries(anomalies []model.Anomaly, seriesMap map[string][]float64) []model.ClusterResult {
	if len(anomalies) == 0 {
		return nil
	}

	n := len(anomalies)
	anomalyList := make([]anomalyWithSeries, n)
	for i, a := range anomalies {
		anomalyList[i] = anomalyWithSeries{
			anomaly:    a,
			seriesData: seriesMap[a.Metric],
			metricName: a.Metric,
		}
	}

	adjacency := make([][]int, n)
	for i := 0; i < n; i++ {
		for j := i + 1; j < n; j++ {
			if c.shouldConnect(anomalyList[i], anomalyList[j]) {
				adjacency[i] = append(adjacency[i], j)
				adjacency[j] = append(adjacency[j], i)
			}
		}
	}

	visited := make([]bool, n)
	var clusters []model.ClusterResult
	clusterID := 0

	for i := 0; i < n; i++ {
		if visited[i] {
			continue
		}

		component := dfs(i, adjacency, visited)
		if len(component) < c.minClusterSize {
			continue
		}

		clusterAnomalies := make([]model.Anomaly, 0, len(component))
		for _, idx := range component {
			a := anomalyList[idx].anomaly
			a.ClusterID = clusterID
			clusterAnomalies = append(clusterAnomalies, a)
		}

		clusters = append(clusters, c.buildCluster(clusterAnomalies, clusterID))
		clusterID++
	}

	return clusters
}

func dfs(start int, adjacency [][]int, visited []bool) []int {
	stack := []int{start}
	visited[start] = true
	var component []int

	for len(stack) > 0 {
		node := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		component = append(component, node)

		for _, neighbor := range adjacency[node] {
			if !visited[neighbor] {
				visited[neighbor] = true
				stack = append(stack, neighbor)
			}
		}
	}

	return component
}

func (c *CorrelationClusterer) shouldConnect(a, b anomalyWithSeries) bool {
	timeDiff := math.Abs(float64(a.anomaly.Timestamp.Sub(b.anomaly.Timestamp).Seconds()))
	if timeDiff > c.timeEpsilon.Seconds() {
		return false
	}

	if a.metricName == b.metricName {
		return timeDiff < c.timeEpsilon.Seconds()/2
	}

	if len(a.seriesData) > 10 && len(b.seriesData) > 10 {
		corr := alignment.CrossCorrelationWithDTW(a.seriesData, b.seriesData)
		if math.Abs(corr) >= c.correlationThreshold {
			return true
		}
	}

	if a.anomaly.Direction != "" && b.anomaly.Direction != "" {
		if a.anomaly.Direction == b.anomaly.Direction {
			return timeDiff < c.timeEpsilon.Seconds()/2
		}
	}

	return false
}

func (c *CorrelationClusterer) buildCluster(anomalies []model.Anomaly, clusterID int) model.ClusterResult {
	var minTime, maxTime time.Time
	totalScore := 0.0
	metricSet := make(map[string]bool)
	directionSet := make(map[model.AnomalyDirection]int)

	for i, a := range anomalies {
		if i == 0 {
			minTime = a.Timestamp
			maxTime = a.Timestamp
		} else {
			if a.Timestamp.Before(minTime) {
				minTime = a.Timestamp
			}
			if a.Timestamp.After(maxTime) {
				maxTime = a.Timestamp
			}
		}
		totalScore += a.Score
		metricSet[a.Metric] = true
		directionSet[a.Direction]++
	}

	size := len(anomalies)
	avgScore := totalScore / float64(size)
	numMetrics := len(metricSet)

	severity := c.determineSeverity(avgScore, size, numMetrics, directionSet)

	return model.ClusterResult{
		ClusterID:  clusterID,
		Anomalies:  anomalies,
		CenterTime: minTime.Add(maxTime.Sub(minTime) / 2),
		Size:       size,
		Severity:   severity,
	}
}

func (c *CorrelationClusterer) determineSeverity(avgScore float64, size, numMetrics int, directions map[model.AnomalyDirection]int) model.AlertSeverity {
	scoreWeight := math.Min(avgScore/3.0, 1.0)
	sizeWeight := math.Min(float64(size)/5.0, 1.0)
	metricWeight := math.Min(float64(numMetrics)/3.0, 1.0)

	multiDirection := len(directions) > 1
	multiDirWeight := 0.0
	if multiDirection {
		multiDirWeight = 0.3
	}

	combinedScore := scoreWeight*0.4 + sizeWeight*0.3 + metricWeight*0.3 + multiDirWeight

	if combinedScore >= 0.75 {
		return model.SeverityCritical
	}
	if combinedScore >= 0.45 {
		return model.SeverityWarning
	}
	return model.SeverityInfo
}

func (c *CorrelationClusterer) ClusterAnomaliesByCorrelation(anomalies []model.Anomaly, timeSeries []model.TimeSeries) []model.ClusterResult {
	seriesMap := make(map[string][]float64)
	for _, ts := range timeSeries {
		data := make([]float64, len(ts.Points))
		for i, p := range ts.Points {
			data[i] = p.Value
		}
		seriesMap[ts.Name] = data
	}

	for _, a := range anomalies {
		if _, ok := seriesMap[a.Metric]; !ok {
			seriesMap[a.Metric] = []float64{a.Value}
		}
	}

	return c.ClusterWithSeries(anomalies, seriesMap)
}

type MetricCorrelation struct {
	MetricA     string
	MetricB     string
	Correlation float64
	DTWDistance float64
}

func ComputeMetricCorrelationMatrix(timeSeries []model.TimeSeries) []MetricCorrelation {
	var correlations []MetricCorrelation

	for i := 0; i < len(timeSeries); i++ {
		for j := i + 1; j < len(timeSeries); j++ {
			dataA := extractValues(timeSeries[i].Points)
			dataB := extractValues(timeSeries[j].Points)

			if len(dataA) < 5 || len(dataB) < 5 {
				continue
			}

			corr := alignment.CrossCorrelationWithDTW(dataA, dataB)
			dtwDist := alignment.FastDTW(dataA, dataB, 10)

			correlations = append(correlations, MetricCorrelation{
				MetricA:     timeSeries[i].Name,
				MetricB:     timeSeries[j].Name,
				Correlation: corr,
				DTWDistance: dtwDist,
			})
		}
	}

	sort.Slice(correlations, func(i, j int) bool {
		return math.Abs(correlations[i].Correlation) > math.Abs(correlations[j].Correlation)
	})

	return correlations
}

func extractValues(points []model.TimeSeriesPoint) []float64 {
	values := make([]float64, len(points))
	for i, p := range points {
		values[i] = p.Value
	}
	return values
}

func GroupAnomaliesByMetric(anomalies []model.Anomaly) map[string][]model.Anomaly {
	groups := make(map[string][]model.Anomaly)
	for _, a := range anomalies {
		groups[a.Metric] = append(groups[a.Metric], a)
	}
	return groups
}

func (c *CorrelationClusterer) FindRelatedMetrics(metric string, correlations []MetricCorrelation, threshold float64) []string {
	var related []string
	seen := make(map[string]bool)

	for _, corr := range correlations {
		if math.Abs(corr.Correlation) >= threshold {
			if corr.MetricA == metric && !seen[corr.MetricB] {
				related = append(related, corr.MetricB)
				seen[corr.MetricB] = true
			}
			if corr.MetricB == metric && !seen[corr.MetricA] {
				related = append(related, corr.MetricA)
				seen[corr.MetricA] = true
			}
		}
	}

	return related
}
