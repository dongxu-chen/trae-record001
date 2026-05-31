package alignment

import (
	"math"
)

type DTWResult struct {
	Distance    float64
	Path        [][2]int
	AlignedA    []float64
	AlignedB    []float64
	TimeWarp    []float64
}

func euclideanDistance(a, b float64) float64 {
	return math.Abs(a - b)
}

func DTWDistance(a, b []float64) float64 {
	m := len(a)
	n := len(b)
	if m == 0 || n == 0 {
		return math.MaxFloat64
	}

	dp := make([][]float64, m+1)
	for i := range dp {
		dp[i] = make([]float64, n+1)
		for j := range dp[i] {
			dp[i][j] = math.MaxFloat64
		}
	}
	dp[0][0] = 0

	for i := 1; i <= m; i++ {
		for j := 1; j <= n; j++ {
			cost := euclideanDistance(a[i-1], b[j-1])
			dp[i][j] = cost + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
		}
	}

	return dp[m][n]
}

func DTW(a, b []float64) DTWResult {
	m := len(a)
	n := len(b)
	if m == 0 || n == 0 {
		return DTWResult{}
	}

	window := max(m, n) / 4
	if window < 10 {
		window = 10
	}

	dp := make([][]float64, m+1)
	for i := range dp {
		dp[i] = make([]float64, n+1)
		for j := range dp[i] {
			dp[i][j] = math.MaxFloat64
		}
	}
	dp[0][0] = 0

	for i := 1; i <= m; i++ {
		startJ := max(1, i-window)
		endJ := min(n, i+window)
		for j := startJ; j <= endJ; j++ {
			cost := euclideanDistance(a[i-1], b[j-1])
			dp[i][j] = cost + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
		}
	}

	path := backtrackPath(dp, m, n)

	alignedA, alignedB := alignSeries(a, b, path)
	timeWarp := computeTimeWarp(path, m, n)

	return DTWResult{
		Distance: dp[m][n] / float64(len(path)),
		Path:     path,
		AlignedA: alignedA,
		AlignedB: alignedB,
		TimeWarp: timeWarp,
	}
}

func backtrackPath(dp [][]float64, m, n int) [][2]int {
	var path [][2]int
	i, j := m, n

	for i > 0 || j > 0 {
		path = append([][2]int{{i - 1, j - 1}}, path...)

		if i == 0 {
			j--
		} else if j == 0 {
			i--
		} else {
			minPrev := min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
			if minPrev == dp[i-1][j-1] {
				i--
				j--
			} else if minPrev == dp[i-1][j] {
				i--
			} else {
				j--
			}
		}
	}

	return path
}

func alignSeries(a, b []float64, path [][2]int) ([]float64, []float64) {
	alignedA := make([]float64, len(path))
	alignedB := make([]float64, len(path))

	for idx, p := range path {
		i, j := p[0], p[1]
		if i >= 0 && i < len(a) {
			alignedA[idx] = a[i]
		}
		if j >= 0 && j < len(b) {
			alignedB[idx] = b[j]
		}
	}

	return alignedA, alignedB
}

func computeTimeWarp(path [][2]int, m, n int) []float64 {
	warp := make([]float64, len(path))
	for idx, p := range path {
		i, j := float64(p[0]), float64(p[1])
		normI := i / float64(m-1)
		normJ := j / float64(n-1)
		warp[idx] = normI - normJ
	}
	return warp
}

func FastDTW(a, b []float64, radius int) float64 {
	m := len(a)
	n := len(b)

	if m <= radius*2+1 || n <= radius*2+1 {
		return DTWDistance(a, b)
	}

	shrinkFactor := 2
	shrunkA := downsample(a, shrinkFactor)
	shrunkB := downsample(b, shrinkFactor)

	lowResPath := FastDTWPath(shrunkA, shrunkB, radius)

	window := expandWarpPath(lowResPath, m, n, shrinkFactor, radius)

	return constrainedDTW(a, b, window)
}

func FastDTWPath(a, b []float64, radius int) [][2]int {
	result := DTW(a, b)
	return result.Path
}

func downsample(data []float64, factor int) []float64 {
	n := len(data)
	result := make([]float64, (n+factor-1)/factor)

	for i := range result {
		start := i * factor
		end := start + factor
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

func expandWarpPath(path [][2]int, origM, origN, factor, radius int) [][2]int {
	window := make([][2]int, 0, len(path)*factor*2)

	for _, p := range path {
		baseI := p[0] * factor
		baseJ := p[1] * factor

		for di := -radius; di <= radius+factor-1; di++ {
			for dj := -radius; dj <= radius+factor-1; dj++ {
				i := baseI + di
				j := baseJ + dj
				if i >= 0 && i < origM && j >= 0 && j < origN {
					window = append(window, [2]int{i, j})
				}
			}
		}
	}

	windowSet := make(map[[2]int]bool)
	for _, w := range window {
		windowSet[w] = true
	}

	uniqueWindow := make([][2]int, 0, len(windowSet))
	for w := range windowSet {
		uniqueWindow = append(uniqueWindow, w)
	}

	return uniqueWindow
}

func constrainedDTW(a, b []float64, window [][2]int) float64 {
	m := len(a)
	n := len(b)

	cellMap := make(map[[2]int]bool)
	for _, w := range window {
		cellMap[w] = true
	}

	dp := make(map[[2]int]float64)
	dp[[2]int{0, 0}] = 0

	for _, w := range window {
		i, j := w[0], w[1]
		if i == 0 && j == 0 {
			continue
		}

		cost := euclideanDistance(a[i], b[j])
		minPrev := math.MaxFloat64

		if v, ok := dp[[2]int{i - 1, j}]; ok && v < minPrev {
			minPrev = v
		}
		if v, ok := dp[[2]int{i, j - 1}]; ok && v < minPrev {
			minPrev = v
		}
		if v, ok := dp[[2]int{i - 1, j - 1}]; ok && v < minPrev {
			minPrev = v
		}

		if minPrev < math.MaxFloat64 {
			dp[[2]int{i, j}] = cost + minPrev
		}
	}

	if v, ok := dp[[2]int{m - 1, n - 1}]; ok {
		return v / float64(len(window))
	}
	return DTWDistance(a, b)
}

func min(vals ...float64) float64 {
	m := vals[0]
	for _, v := range vals[1:] {
		if v < m {
			m = v
		}
	}
	return m
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func min(a, b, c float64) float64 {
	m := a
	if b < m {
		m = b
	}
	if c < m {
		m = c
	}
	return m
}

func max(a, b, c int) int {
	m := a
	if b > m {
		m = b
	}
	if c > m {
		m = c
	}
	return m
}

func ShapeBasedDTW(a, b []float64) float64 {
	normA := zNormalize(a)
	normB := zNormalize(b)
	return DTWDistance(normA, normB)
}

func zNormalize(data []float64) []float64 {
	n := len(data)
	if n == 0 {
		return data
	}

	m := mean(data)
	variance := 0.0
	for _, v := range data {
		variance += (v - m) * (v - m)
	}
	std := math.Sqrt(variance / float64(n))
	if std == 0 {
		std = 1
	}

	result := make([]float64, n)
	for i, v := range data {
		result[i] = (v - m) / std
	}
	return result
}

func CrossCorrelationWithDTW(a, b []float64) float64 {
	result := DTW(a, b)
	if len(result.AlignedA) == 0 {
		return 0
	}

	return pearsonCorrelationSimple(result.AlignedA, result.AlignedB)
}

func pearsonCorrelationSimple(x, y []float64) float64 {
	n := len(x)
	if n != len(y) || n < 2 {
		return 0
	}

	meanX := mean(x)
	meanY := mean(y)

	covXY := 0.0
	varX := 0.0
	varY := 0.0

	for i := 0; i < n; i++ {
		dx := x[i] - meanX
		dy := y[i] - meanY
		covXY += dx * dy
		varX += dx * dx
		varY += dy * dy
	}

	if varX == 0 || varY == 0 {
		return 0
	}

	return covXY / math.Sqrt(varX*varY)
}

func mean(data []float64) float64 {
	if len(data) == 0 {
		return 0
	}
	sum := 0.0
	for _, v := range data {
		sum += v
	}
	return sum / float64(len(data))
}
