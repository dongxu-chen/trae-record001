package cluster

import (
	"fmt"
	"math"
	"math/rand"
	"sync"

	"heatcache/internal/parser"
)

type Cluster struct {
	ID       int
	Centroid []float64
	Members  []*QueryClusterItem
}

type QueryClusterItem struct {
	Query      *parser.ParsedQuery
	Vector     []float64
	Frequency  int
	AvgLatency float64
}

type KMeansConfig struct {
	K             int
	MaxIterations int
	Convergence   float64
	DistanceMetric string
}

type KMeansClusterer struct {
	config  KMeansConfig
	clusters []*Cluster
	rng     *rand.Rand
	mu      sync.Mutex
}

func NewKMeansClusterer(config KMeansConfig) *KMeansClusterer {
	if config.K <= 0 {
		config.K = 5
	}
	if config.MaxIterations <= 0 {
		config.MaxIterations = 100
	}
	if config.Convergence <= 0 {
		config.Convergence = 0.001
	}
	if config.DistanceMetric == "" {
		config.DistanceMetric = "euclidean"
	}
	return &KMeansClusterer{
		config: config,
		rng:    rand.New(rand.NewSource(42)),
	}
}

func (km *KMeansClusterer) Cluster(items []*QueryClusterItem) ([]*Cluster, error) {
	if len(items) == 0 {
		return nil, fmt.Errorf("no items to cluster")
	}
	if len(items) < km.config.K {
		km.config.K = len(items)
	}

	dim := len(items[0].Vector)
	centroids := km.initializeCentroids(items, dim)

	for iter := 0; iter < km.config.MaxIterations; iter++ {
		assignments := km.assignToClusters(items, centroids)
		newCentroids := km.recalculateCentroids(items, assignments, dim)

		if km.hasConverged(centroids, newCentroids) {
			break
		}
		centroids = newCentroids
	}

	assignments := km.assignToClusters(items, centroids)
	clusters := make([]*Cluster, km.config.K)
	for i := range clusters {
		clusters[i] = &Cluster{
			ID:       i,
			Centroid: centroids[i],
			Members:  make([]*QueryClusterItem, 0),
		}
	}
	for idx, clusterID := range assignments {
		clusters[clusterID].Members = append(clusters[clusterID].Members, items[idx])
	}

	km.mu.Lock()
	km.clusters = clusters
	km.mu.Unlock()

	return clusters, nil
}

func (km *KMeansClusterer) initializeCentroids(items []*QueryClusterItem, dim int) [][]float64 {
	centroids := make([][]float64, km.config.K)
	perm := km.rng.Perm(len(items))

	k := km.config.K
	if k > len(items) {
		k = len(items)
	}

	for i := 0; i < k; i++ {
		centroid := make([]float64, dim)
		copy(centroid, items[perm[i]].Vector)
		centroids[i] = centroid
	}
	return centroids
}

func (km *KMeansClusterer) assignToClusters(items []*QueryClusterItem, centroids [][]float64) []int {
	assignments := make([]int, len(items))
	for i, item := range items {
		minDist := math.MaxFloat64
		bestCluster := 0
		for j, centroid := range centroids {
			d := km.distance(item.Vector, centroid)
			if d < minDist {
				minDist = d
				bestCluster = j
			}
		}
		assignments[i] = bestCluster
	}
	return assignments
}

func (km *KMeansClusterer) recalculateCentroids(items []*QueryClusterItem, assignments []int, dim int) [][]float64 {
	centroids := make([][]float64, km.config.K)
	counts := make([]int, km.config.K)

	for i := range centroids {
		centroids[i] = make([]float64, dim)
	}

	for i, item := range items {
		c := assignments[i]
		counts[c]++
		for d := 0; d < dim; d++ {
			centroids[c][d] += item.Vector[d]
		}
	}

	for i := range centroids {
		if counts[i] > 0 {
			for d := 0; d < dim; d++ {
				centroids[i][d] /= float64(counts[i])
			}
		}
	}

	return centroids
}

func (km *KMeansClusterer) hasConverged(old, new [][]float64) bool {
	for i := range old {
		d := km.distance(old[i], new[i])
		if d > km.config.Convergence {
			return false
		}
	}
	return true
}

func (km *KMeansClusterer) distance(a, b []float64) float64 {
	switch km.config.DistanceMetric {
	case "manhattan":
		return manhattanDistance(a, b)
	case "cosine":
		return cosineDistance(a, b)
	default:
		return euclideanDistance(a, b)
	}
}

func euclideanDistance(a, b []float64) float64 {
	sum := 0.0
	for i := range a {
		diff := a[i] - b[i]
		sum += diff * diff
	}
	return math.Sqrt(sum)
}

func manhattanDistance(a, b []float64) float64 {
	sum := 0.0
	for i := range a {
		sum += math.Abs(a[i] - b[i])
	}
	return sum
}

func cosineDistance(a, b []float64) float64 {
	dot := 0.0
	normA := 0.0
	normB := 0.0
	for i := range a {
		dot += a[i] * b[i]
		normA += a[i] * a[i]
		normB += b[i] * b[i]
	}
	if normA == 0 || normB == 0 {
		return 1.0
	}
	return 1.0 - dot/(math.Sqrt(normA)*math.Sqrt(normB))
}

func (c *Cluster) AverageFrequency() float64 {
	if len(c.Members) == 0 {
		return 0
	}
	total := 0.0
	for _, m := range c.Members {
		total += float64(m.Frequency)
	}
	return total / float64(len(c.Members))
}

func (c *Cluster) AverageLatency() float64 {
	if len(c.Members) == 0 {
		return 0
	}
	total := 0.0
	for _, m := range c.Members {
		total += m.AvgLatency
	}
	return total / float64(len(c.Members))
}

func (c *Cluster) TotalFrequency() int {
	total := 0
	for _, m := range c.Members {
		total += m.Frequency
	}
	return total
}

func (c *Cluster) HotScore() float64 {
	avgFreq := c.AverageFrequency()
	avgLat := c.AverageLatency()
	return avgFreq*0.6 + avgLat*0.4
}

type ClusterAnalyzer struct {
	clusterer *KMeansClusterer
}

func NewClusterAnalyzer(k int) *ClusterAnalyzer {
	return &ClusterAnalyzer{
		clusterer: NewKMeansClusterer(KMeansConfig{
			K:             k,
			MaxIterations: 100,
			Convergence:   0.001,
			DistanceMetric: "euclidean",
		}),
	}
}

func (ca *ClusterAnalyzer) AnalyzeAndRank(items []*QueryClusterItem) ([]*Cluster, error) {
	clusters, err := ca.clusterer.Cluster(items)
	if err != nil {
		return nil, err
	}

	ranked := make([]*Cluster, len(clusters))
	copy(ranked, clusters)

	for i := 0; i < len(ranked)-1; i++ {
		for j := i + 1; j < len(ranked); j++ {
			if ranked[i].HotScore() < ranked[j].HotScore() {
				ranked[i], ranked[j] = ranked[j], ranked[i]
			}
		}
	}

	return ranked, nil
}

func (ca *ClusterAnalyzer) ExtractHotQueries(clusters []*Cluster, topN int) []*QueryClusterItem {
	var allItems []*QueryClusterItem
	for _, c := range clusters {
		allItems = append(allItems, c.Members...)
	}

	for i := 0; i < len(allItems)-1; i++ {
		for j := i + 1; j < len(allItems); j++ {
			scoreI := float64(allItems[i].Frequency)*0.6 + allItems[i].AvgLatency*0.4
			scoreJ := float64(allItems[j].Frequency)*0.6 + allItems[j].AvgLatency*0.4
			if scoreI < scoreJ {
				allItems[i], allItems[j] = allItems[j], allItems[i]
			}
		}
	}

	if topN > len(allItems) {
		topN = len(allItems)
	}
	return allItems[:topN]
}

func EstimateOptimalK(items []*QueryClusterItem, maxK int) int {
	if len(items) <= 1 {
		return 1
	}
	if maxK > len(items) {
		maxK = len(items)
	}

	var prevInertia float64
	bestK := 2
	bestDiff := math.MaxFloat64

	for k := 2; k <= maxK; k++ {
		km := NewKMeansClusterer(KMeansConfig{
			K:             k,
			MaxIterations: 50,
			Convergence:   0.01,
		})
		clusters, err := km.Cluster(items)
		if err != nil {
			continue
		}

		inertia := 0.0
		for _, c := range clusters {
			for _, m := range c.Members {
				inertia += euclideanDistance(m.Vector, c.Centroid)
			}
		}

		if k > 2 {
			diff := math.Abs(prevInertia - inertia)
			if diff < bestDiff {
				bestDiff = diff
				bestK = k
			}
		}
		prevInertia = inertia
	}

	return bestK
}
