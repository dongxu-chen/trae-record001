package clustering

import (
	"math"
	"time"

	"anomaly-detector/model"
)

type DBSCAN struct {
	eps    time.Duration
	minPts int
}

func NewDBSCAN(eps time.Duration, minPts int) *DBSCAN {
	return &DBSCAN{eps: eps, minPts: minPts}
}

func timeDistance(a, b time.Time) float64 {
	diff := a.Sub(b)
	if diff < 0 {
		diff = -diff
	}
	return diff.Seconds()
}

func (d *DBSCAN) Cluster(anomalies []model.Anomaly) []model.ClusterResult {
	if len(anomalies) == 0 {
		return nil
	}

	n := len(anomalies)
	labels := make([]int, n)
	for i := range labels {
		labels[i] = -1
	}

	clusterID := 0

	for i := 0; i < n; i++ {
		if labels[i] != -1 {
			continue
		}

		neighbors := d.rangeQuery(anomalies, i)

		if len(neighbors) < d.minPts {
			labels[i] = -2
			continue
		}

		labels[i] = clusterID

		seedSet := make([]int, len(neighbors))
		copy(seedSet, neighbors)

		for len(seedSet) > 0 {
			current := seedSet[0]
			seedSet = seedSet[1:]

			if labels[current] == -2 {
				labels[current] = clusterID
			}
			if labels[current] != -1 {
				continue
			}

			labels[current] = clusterID
			currentNeighbors := d.rangeQuery(anomalies, current)

			if len(currentNeighbors) >= d.minPts {
				seedSet = append(seedSet, currentNeighbors...)
			}
		}

		clusterID++
	}

	return d.buildClusters(anomalies, labels, clusterID)
}

func (d *DBSCAN) rangeQuery(anomalies []model.Anomaly, idx int) []int {
	var neighbors []int
	epsSeconds := d.eps.Seconds()

	for i := 0; i < len(anomalies); i++ {
		if i == idx {
			continue
		}
		dist := timeDistance(anomalies[idx].Timestamp, anomalies[i].Timestamp)
		if dist <= epsSeconds {
			neighbors = append(neighbors, i)
		}
	}

	return neighbors
}

func (d *DBSCAN) buildClusters(anomalies []model.Anomaly, labels []int, numClusters int) []model.ClusterResult {
	clusters := make([]model.ClusterResult, numClusters)
	for i := 0; i < numClusters; i++ {
		clusters[i] = model.ClusterResult{
			ClusterID: i,
		}
	}

	for i, label := range labels {
		if label >= 0 && label < numClusters {
			anomalies[i].ClusterID = label
			clusters[label].Anomalies = append(clusters[label].Anomalies, anomalies[i])
		}
	}

	for i := range clusters {
		clusters[i].Size = len(clusters[i].Anomalies)
		if clusters[i].Size == 0 {
			continue
		}

		var minTime, maxTime time.Time
		totalDeviation := 0.0
		hasDirection := make(map[model.AnomalyDirection]int)

		for j, a := range clusters[i].Anomalies {
			if j == 0 {
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
			totalDeviation += a.Deviation
			hasDirection[a.Direction]++
		}

		clusters[i].CenterTime = minTime.Add(maxTime.Sub(minTime) / 2)
		avgDeviation := totalDeviation / float64(clusters[i].Size)

		clusters[i].Severity = determineSeverity(avgDeviation, clusters[i].Size, hasDirection)
	}

	return clusters
}

func determineSeverity(avgDeviation float64, size int, directions map[model.AnomalyDirection]int) model.AlertSeverity {
	devScore := math.Min(avgDeviation/3.0, 1.0)
	sizeScore := math.Min(float64(size)/5.0, 1.0)

	multiDirection := len(directions) > 1
	combinedScore := devScore*0.6 + sizeScore*0.4
	if multiDirection {
		combinedScore *= 1.2
	}

	if combinedScore >= 0.7 {
		return model.SeverityCritical
	}
	if combinedScore >= 0.4 {
		return model.SeverityWarning
	}
	return model.SeverityInfo
}
