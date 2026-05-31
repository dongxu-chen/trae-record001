package detector

import (
	"math"
	"sort"
)

type SESDResult struct {
	Index      int
	Value      float64
	Expected   float64
	Deviation  float64
	Score      float64
	PValue     float64
	IsAnomaly  bool
}

func robustMean(data []float64, k float64) float64 {
	n := len(data)
	if n == 0 {
		return 0
	}

	m := median(data)
	madVal := mad(data)
	if madVal == 0 {
		madVal = 1
	}

	threshold := k * 1.4826 * madVal
	sum := 0.0
	count := 0

	for _, v := range data {
		if math.Abs(v-m) <= threshold {
			sum += v
			count++
		}
	}

	if count == 0 {
		return m
	}
	return sum / float64(count)
}

func robustStd(data []float64, k float64) float64 {
	n := len(data)
	if n < 2 {
		return 0
	}

	m := robustMean(data, k)
	variance := 0.0
	count := 0

	for _, v := range data {
		variance += (v - m) * (v - m)
		count++
	}

	if count < 2 {
		return 1
	}

	return math.Sqrt(variance / float64(count-1))
}

func generalizedESD(data []float64, maxAnomalies int, alpha float64, robust bool) []SESDFResult {
	n := len(data)
	if n < 3 || maxAnomalies <= 0 {
		return nil
	}

	if maxAnomalies > n/2 {
		maxAnomalies = n / 2
	}

	anomalies := make([]SESDFResult, 0)
	workingData := make([]float64, n)
	copy(workingData, data)
	indices := make([]int, n)
	for i := range indices {
		indices[i] = i
	}

	for k := 0; k < maxAnomalies; k++ {
		m := 0.0
		sd := 0.0
		if robust {
			m = robustMean(workingData, 3.0)
			sd = robustStd(workingData, 3.0)
		} else {
			m = mean(workingData)
			variance := 0.0
			for _, v := range workingData {
				variance += (v - m) * (v - m)
			}
			sd = math.Sqrt(variance / float64(len(workingData)-1))
		}

		if sd == 0 {
			sd = 1
		}

		maxIdx := 0
		maxStat := 0.0
		for i, v := range workingData {
			stat := math.Abs(v - m) / sd
			if stat > maxStat {
				maxStat = stat
				maxIdx = i
			}
		}

		curN := len(workingData)
		df := curN - 2
		if df < 1 {
			break
		}

		tCritical := criticalValue(float64(df), alpha/float64(maxAnomalies-k))
		tValue := maxStat * math.Sqrt(float64(df)) / math.Sqrt(float64(curN-1)-maxStat*maxStat)

		expected := m
		value := workingData[maxIdx]
		deviation := math.Abs(value - expected)

		result := SESDFResult{
			Index:     indices[maxIdx],
			Value:     value,
			Expected:  expected,
			Deviation: deviation,
			Score:     maxStat,
			IsAnomaly: math.Abs(tValue) > tCritical,
		}

		if result.IsAnomaly {
			anomalies = append(anomalies, result)
		} else {
			break
		}

		workingData = append(workingData[:maxIdx], workingData[maxIdx+1:]...)
		indices = append(indices[:maxIdx], indices[maxIdx+1:]...)
	}

	return anomalies
}

func criticalValue(df, alpha float64) float64 {
	p := 1 - alpha/2
	approx := normQuantile(p) * math.Sqrt(df/math.Max(0.001, df-0.5))
	return approx
}

func normQuantile(p float64) float64 {
	if p <= 0 {
		return -math.MaxFloat64
	}
	if p >= 1 {
		return math.MaxFloat64
	}

	if p == 0.5 {
		return 0
	}

	a := [4]float64{2.50662823884, -18.61500062529, 41.39119773534, -25.44106049637}
	b := [4]float64{-8.47351093090, 23.08336743743, -21.06224101826, 3.13082909833}
	c := [9]float64{0.3374754822726147, 0.9761690190917186, 0.1607979714918209,
		0.0276438810333863, 0.0038405729373609, 0.0003951896511919,
		0.0000321767881768, 0.0000002888167364, 0.0000003960315187}

	var y float64
	if p < 0.5 {
		y = math.Sqrt(-2 * math.Log(p))
	} else {
		y = math.Sqrt(-2 * math.Log(1 - p))
	}

	y2 := y * y
	y3 := y2 * y
	y4 := y3 * y

	num := a[0] + a[1]*y + a[2]*y2 + a[3]*y3
	den := 1 + b[0]*y + b[1]*y2 + b[2]*y3 + b[3]*y4
	x := y - num/den

	if p < 0.5 {
		return -x
	}
	return x
}

type SESDFResult struct {
	Index      int
	Value      float64
	Expected   float64
	Deviation  float64
	Score      float64
	IsAnomaly  bool
}

func S_ESDDetect(data []float64, period int, maxAnomalies int, alpha float64, direction string) []SESDFResult {
	n := len(data)
	if n < 10 {
		return nil
	}

	stlResult := STLDecompose(data, period, 5)

	remainder := make([]float64, n)
	switch direction {
	case "up":
		for i := range data {
			if stlResult.Remainder[i] > 0 {
				remainder[i] = stlResult.Remainder[i]
			} else {
				remainder[i] = 0
			}
		}
	case "down":
		for i := range data {
			if stlResult.Remainder[i] < 0 {
				remainder[i] = -stlResult.Remainder[i]
			} else {
				remainder[i] = 0
			}
		}
	default:
		for i := range data {
			remainder[i] = math.Abs(stlResult.Remainder[i])
		}
	}

	esdResults := generalizedESD(remainder, maxAnomalies, alpha, true)

	for i := range esdResults {
		idx := esdResults[i].Index
		esdResults[i].Expected = stlResult.Trend[idx] + stlResult.Seasonal[idx]
		esdResults[i].Value = data[idx]
		esdResults[i].Deviation = math.Abs(data[idx] - esdResults[i].Expected)
	}

	return esdResults
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
