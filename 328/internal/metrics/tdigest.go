package metrics

import (
	"math"
	"sort"
	"sync"
)

type Centroid struct {
	Mean   float64
	Weight float64
}

type TDigest struct {
	mu          sync.RWMutex
	centroids   []Centroid
	compression float64
	count       float64
	maxCentroids int
}

func NewTDigest(compression float64, maxCentroids int) *TDigest {
	if compression <= 0 {
		compression = 100
	}
	if maxCentroids <= 0 {
		maxCentroids = 1000
	}
	return &TDigest{
		centroids:   make([]Centroid, 0, maxCentroids),
		compression: compression,
		maxCentroids: maxCentroids,
	}
}

func (t *TDigest) Add(value float64, weight float64) {
	t.mu.Lock()
	defer t.mu.Unlock()

	t.add(value, weight)
	t.count += weight
	t.compress()
}

func (t *TDigest) add(value float64, weight float64) {
	t.centroids = append(t.centroids, Centroid{Mean: value, Weight: weight})
}

func (t *TDigest) compress() {
	if len(t.centroids) <= 1 {
		return
	}

	sort.Slice(t.centroids, func(i, j int) bool {
		return t.centroids[i].Mean < t.centroids[j].Mean
	})

	merged := make([]Centroid, 0, t.maxCentroids)
	var currentMean, currentWeight float64
	var countSoFar float64

	for _, c := range t.centroids {
		if currentWeight == 0 {
			currentMean = c.Mean
			currentWeight = c.Weight
			continue
		}

		proposedWeight := currentWeight + c.Weight
		quantile := (countSoFar + currentWeight/2) / t.count
		threshold := t.threshold(quantile)

		if proposedWeight <= threshold {
			currentMean = (currentMean*currentWeight + c.Mean*c.Weight) / proposedWeight
			currentWeight = proposedWeight
		} else {
			merged = append(merged, Centroid{Mean: currentMean, Weight: currentWeight})
			countSoFar += currentWeight
			currentMean = c.Mean
			currentWeight = c.Weight
		}
	}

	if currentWeight > 0 {
		merged = append(merged, Centroid{Mean: currentMean, Weight: currentWeight})
	}

	t.centroids = merged
}

func (t *TDigest) threshold(quantile float64) float64 {
	if quantile <= 0 || quantile >= 1 {
		return 1
	}
	k := t.compression * (quantile*(1-quantile) + 1e-9)
	return math.Max(1, t.count/k)
}

func (t *TDigest) Quantile(q float64) float64 {
	t.mu.RLock()
	defer t.mu.RUnlock()

	if t.count == 0 || len(t.centroids) == 0 {
		return 0
	}
	if q <= 0 {
		return t.centroids[0].Mean
	}
	if q >= 1 {
		return t.centroids[len(t.centroids)-1].Mean
	}

	target := q * t.count
	var countSoFar float64

	for i := 0; i < len(t.centroids); i++ {
		c := t.centroids[i]
		if countSoFar+c.Weight >= target {
			if i == 0 {
				return c.Mean
			}
			prev := t.centroids[i-1]
			prevCount := countSoFar - c.Weight/2
			currCount := countSoFar + c.Weight/2
			frac := (target - prevCount) / (currCount - prevCount)
			return prev.Mean + frac*(c.Mean-prev.Mean)
		}
		countSoFar += c.Weight
	}

	return t.centroids[len(t.centroids)-1].Mean
}

func (t *TDigest) Count() float64 {
	t.mu.RLock()
	defer t.mu.RUnlock()
	return t.count
}

func (t *TDigest) Reset() {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.centroids = t.centroids[:0]
	t.count = 0
}

func (t *TDigest) Merge(other *TDigest) {
	t.mu.Lock()
	defer t.mu.Unlock()

	other.mu.RLock()
	defer other.mu.RUnlock()

	for _, c := range other.centroids {
		t.add(c.Mean, c.Weight)
		t.count += c.Weight
	}
	t.compress()
}
