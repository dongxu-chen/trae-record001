package detector

import (
	"math"
	"sort"
)

func loessSmooth(data []float64, window int) []float64 {
	n := len(data)
	result := make([]float64, n)
	halfWindow := window / 2

	for i := range data {
		start := i - halfWindow
		end := i + halfWindow
		if start < 0 {
			start = 0
		}
		if end >= n {
			end = n - 1
		}

		weightedSum := 0.0
		weightTotal := 0.0

		maxDist := float64(halfWindow)
		if maxDist == 0 {
			maxDist = 1
		}

		for j := start; j <= end; j++ {
			dist := math.Abs(float64(j - i))
			weight := math.Max(0, 1-math.Pow(dist/maxDist, 3))
			weight = weight * weight * weight
			weightedSum += data[j] * weight
			weightTotal += weight
		}

		if weightTotal > 0 {
			result[i] = weightedSum / weightTotal
		} else {
			result[i] = data[i]
		}
	}

	return result
}

func movingAverage(data []float64, window int) []float64 {
	n := len(data)
	result := make([]float64, n)
	halfWindow := window / 2

	for i := range data {
		start := i - halfWindow
		end := i + halfWindow + 1
		if start < 0 {
			start = 0
		}
		if end > n {
			end = n
		}

		sum := 0.0
		for j := start; j < end; j++ {
			sum += data[j]
		}
		result[i] = sum / float64(end-start)
	}

	return result
}

type STLResult struct {
	Seasonal []float64
	Trend    []float64
	Remainder []float64
}

func STLDecompose(data []float64, period int, iterations int) STLResult {
	n := len(data)
	if n < 2*period {
		trend := movingAverage(data, period)
		remainder := make([]float64, n)
		for i := range data {
			remainder[i] = data[i] - trend[i]
		}
		return STLResult{
			Seasonal:  make([]float64, n),
			Trend:     trend,
			Remainder: remainder,
		}
	}

	seasonal := make([]float64, n)
	trend := make([]float64, n)

	detrended := make([]float64, n)
	for i := range data {
		detrended[i] = data[i]
	}

	for iter := 0; iter < iterations; iter++ {
		cycleSubseries := make([][]float64, period)
		for i := 0; i < period; i++ {
			for j := i; j < n; j += period {
				cycleSubseries[i] = append(cycleSubseries[i], detrended[j])
			}
		}

		smoothedSeasonal := make([]float64, n)
		for i := 0; i < period; i++ {
			if len(cycleSubseries[i]) == 0 {
				continue
			}
			smoothed := loessSmooth(cycleSubseries[i], max(3, len(cycleSubseries[i])/3))
			for j := 0; j < len(smoothed); j++ {
				idx := i + j*period
				if idx < n {
					smoothedSeasonal[idx] = smoothed[j]
				}
			}
		}

		seasonal = loessSmooth(smoothedSeasonal, period)

		seasonalMean := 0.0
		for _, v := range seasonal {
			seasonalMean += v
		}
		seasonalMean /= float64(n)
		for i := range seasonal {
			seasonal[i] -= seasonalMean
		}

		deSeasonalized := make([]float64, n)
		for i := range data {
			deSeasonalized[i] = data[i] - seasonal[i]
		}

		trend = loessSmooth(deSeasonalized, period)

		for i := range data {
			detrended[i] = data[i] - trend[i]
		}
	}

	remainder := make([]float64, n)
	for i := range data {
		remainder[i] = data[i] - trend[i] - seasonal[i]
	}

	return STLResult{
		Seasonal:  seasonal,
		Trend:     trend,
		Remainder: remainder,
	}
}
