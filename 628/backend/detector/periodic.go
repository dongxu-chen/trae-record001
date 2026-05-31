package detector

import (
	"math"
)

func autocorrelation(data []float64, lag int) float64 {
	n := len(data)
	if lag >= n || lag < 0 {
		return 0
	}

	m := mean(data)
	numerator := 0.0
	denominator := 0.0

	for i := 0; i < n; i++ {
		denominator += (data[i] - m) * (data[i] - m)
	}

	if denominator == 0 {
		return 0
	}

	for i := 0; i < n-lag; i++ {
		numerator += (data[i] - m) * (data[i+lag] - m)
	}

	return numerator / denominator
}

func DetectPeriod(data []float64, minPeriod, maxPeriod int) int {
	n := len(data)
	if n < 4 {
		return 0
	}

	if minPeriod < 2 {
		minPeriod = 2
	}
	if maxPeriod > n/2 {
		maxPeriod = n / 2
	}
	if minPeriod > maxPeriod {
		return 0
	}

	bestPeriod := 0
	bestScore := 0.0

	for lag := minPeriod; lag <= maxPeriod; lag++ {
		ac := autocorrelation(data, lag)
		if ac > bestScore {
			bestScore = ac
			bestPeriod = lag
		}
	}

	if bestScore < 0.3 {
		return 0
	}

	secondBest := 0.0
	for lag := minPeriod; lag <= maxPeriod; lag++ {
		if lag == bestPeriod {
			continue
		}
		ac := autocorrelation(data, lag)
		if ac > secondBest {
			secondBest = ac
		}
	}

	if bestScore < secondBest*1.2 {
		return bestPeriod
	}

	return bestPeriod
}

func ComputeFFTPeriod(data []float64, sampleRate float64) int {
	n := len(data)
	if n < 4 {
		return 0
	}

	m := mean(data)
	normalized := make([]float64, n)
	for i := range data {
		normalized[i] = data[i] - m
	}

	windowed := applyHannWindow(normalized)

	magnitude := computeMagnitudes(windowed)

	bestIdx := 0
	bestMag := 0.0
	for i := 1; i < len(magnitude)/2; i++ {
		if magnitude[i] > bestMag {
			bestMag = magnitude[i]
			bestIdx = i
		}
	}

	if bestIdx == 0 {
		return 0
	}

	frequency := float64(bestIdx) / float64(len(magnitude)) * sampleRate
	if frequency == 0 {
		return 0
	}

	period := int(1.0 / frequency)
	if period < 2 || period > n/2 {
		return 0
	}

	return period
}

func applyHannWindow(data []float64) []float64 {
	n := len(data)
	result := make([]float64, n)
	for i := range data {
		w := 0.5 * (1 - math.Cos(2*math.Pi*float64(i)/float64(n-1)))
		result[i] = data[i] * w
	}
	return result
}

func computeMagnitudes(data []float64) []float64 {
	n := len(data)
	real := make([]float64, n)
	imag := make([]float64, n)
	copy(real, data)

	bitReversePermute(real, imag, n)

	for size := 2; size <= n; size *= 2 {
		halfSize := size / 2
		angle := -2 * math.Pi / float64(size)
		wReal := math.Cos(angle)
		wImag := math.Sin(angle)

		for i := 0; i < n; i += size {
			curReal := 1.0
			curImag := 0.0
			for j := 0; j < halfSize; j++ {
				idx1 := i + j
				idx2 := i + j + halfSize
				tReal := curReal*real[idx2] - curImag*imag[idx2]
				tImag := curReal*imag[idx2] + curImag*real[idx2]

				real[idx2] = real[idx1] - tReal
				imag[idx2] = imag[idx1] - tImag
				real[idx1] += tReal
				imag[idx1] += tImag

				newCurReal := curReal*wReal - curImag*wImag
				newCurImag := curReal*wImag + curImag*wReal
				curReal = newCurReal
				curImag = newCurImag
			}
		}

		if size > n/2 {
			break
		}
	}

	magnitude := make([]float64, n)
	for i := 0; i < n; i++ {
		magnitude[i] = math.Sqrt(real[i]*real[i] + imag[i]*imag[i])
	}
	return magnitude
}

func bitReversePermute(real, imag []float64, n int) {
	j := 0
	for i := 1; i < n; i++ {
		bit := n >> 1
		for j&bit != 0 {
			j ^= bit
			bit >>= 1
		}
		j ^= bit
		if i < j {
			real[i], real[j] = real[j], real[i]
			imag[i], imag[j] = imag[j], imag[i]
		}
	}
}
