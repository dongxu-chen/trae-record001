package correlation

import (
	"math"
	"sort"

	"anomaly-detector/alignment"
	"anomaly-detector/model"
)

type Correlator struct {
	significanceLevel float64
	useDTWAlignment   bool
}

func NewCorrelator(significanceLevel float64) *Correlator {
	if significanceLevel <= 0 {
		significanceLevel = 0.05
	}
	return &Correlator{
		significanceLevel: significanceLevel,
		useDTWAlignment:   true,
	}
}

func NewCorrelatorWithDTW(significanceLevel float64, useDTW bool) *Correlator {
	c := NewCorrelator(significanceLevel)
	c.useDTWAlignment = useDTW
	return c
}

func (c *Correlator) Correlate(series []model.TimeSeries) []model.CorrelationResult {
	var results []model.CorrelationResult

	for i := 0; i < len(series); i++ {
		for j := i + 1; j < len(series); j++ {
			dataA := extractSeriesValues(series[i])
			dataB := extractSeriesValues(series[j])

			if len(dataA) < 5 || len(dataB) < 5 {
				continue
			}

			var r float64
			var pValue float64

			if c.useDTWAlignment {
				r = alignment.CrossCorrelationWithDTW(dataA, dataB)
				pValue = computePValue(r, min(len(dataA), len(dataB)))
			} else {
				minLen := len(dataA)
				if len(dataB) < minLen {
					minLen = len(dataB)
				}
				x := make([]float64, minLen)
				y := make([]float64, minLen)
				copy(x, dataA[:minLen])
				copy(y, dataB[:minLen])
				r, pValue = pearsonCorrelation(x, y)
			}

			results = append(results, model.CorrelationResult{
				MetricA:     series[i].Name,
				MetricB:     series[j].Name,
				Coefficient: r,
				PValue:      pValue,
				Significant: pValue < c.significanceLevel,
			})
		}
	}

	sort.Slice(results, func(i, j int) bool {
		return math.Abs(results[i].Coefficient) > math.Abs(results[j].Coefficient)
	})

	return results
}

func (c *Correlator) CorrelateWithDTW(series []model.TimeSeries) []model.CorrelationResult {
	var results []model.CorrelationResult

	for i := 0; i < len(series); i++ {
		for j := i + 1; j < len(series); j++ {
			dataA := extractSeriesValues(series[i])
			dataB := extractSeriesValues(series[j])

			if len(dataA) < 5 || len(dataB) < 5 {
				continue
			}

			dtwResult := alignment.DTW(dataA, dataB)

			if len(dtwResult.AlignedA) >= 5 {
				r, pValue := pearsonCorrelation(dtwResult.AlignedA, dtwResult.AlignedB)

				results = append(results, model.CorrelationResult{
					MetricA:     series[i].Name,
					MetricB:     series[j].Name,
					Coefficient: r,
					PValue:      pValue,
					Significant: pValue < c.significanceLevel && math.Abs(r) >= 0.5,
				})
			}
		}
	}

	sort.Slice(results, func(i, j int) bool {
		return math.Abs(results[i].Coefficient) > math.Abs(results[j].Coefficient)
	})

	return results
}

func (c *Correlator) CorrelateAnomalies(anomalies []model.Anomaly, series []model.TimeSeries) []model.CorrelationResult {
	metricAnomalies := make(map[string][]model.Anomaly)
	for _, a := range anomalies {
		metricAnomalies[a.Metric] = append(metricAnomalies[a.Metric], a)
	}

	var results []model.CorrelationResult
	metrics := make([]string, 0, len(metricAnomalies))
	for m := range metricAnomalies {
		metrics = append(metrics, m)
	}

	seriesMap := make(map[string][]float64)
	for _, s := range series {
		seriesMap[s.Name] = extractSeriesValues(s)
	}

	for i := 0; i < len(metrics); i++ {
		for j := i + 1; j < len(metrics); j++ {
			anomsA := metricAnomalies[metrics[i]]
			anomsB := metricAnomalies[metrics[j]]

			timeOverlap := 0
			for _, a := range anomsA {
				for _, b := range anomsB {
					diff := a.Timestamp.Sub(b.Timestamp).Minutes()
					if diff < 0 {
						diff = -diff
					}
					if diff < 5 {
						timeOverlap++
					}
				}
			}

			baseCorrelation := 0.0
			if dataA, ok := seriesMap[metrics[i]]; ok {
				if dataB, ok := seriesMap[metrics[j]]; ok {
					baseCorrelation = alignment.CrossCorrelationWithDTW(dataA, dataB)
				}
			}

			if timeOverlap > 0 || math.Abs(baseCorrelation) >= 0.3 {
				combinedScore := math.Max(float64(timeOverlap)/float64(max(len(anomsA), len(anomsB))), math.Abs(baseCorrelation))
				results = append(results, model.CorrelationResult{
					MetricA:     metrics[i],
					MetricB:     metrics[j],
					Coefficient: combinedScore,
					Significant: timeOverlap >= 2 || math.Abs(baseCorrelation) >= 0.5,
				})
			}
		}
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Coefficient > results[j].Coefficient
	})

	return results
}

func (c *Correlator) BuildCorrelationMatrix(series []model.TimeSeries) map[string]map[string]float64 {
	matrix := make(map[string]map[string]float64)

	correlations := c.Correlate(series)
	for _, corr := range correlations {
		if matrix[corr.MetricA] == nil {
			matrix[corr.MetricA] = make(map[string]float64)
		}
		if matrix[corr.MetricB] == nil {
			matrix[corr.MetricB] = make(map[string]float64)
		}
		matrix[corr.MetricA][corr.MetricB] = corr.Coefficient
		matrix[corr.MetricB][corr.MetricA] = corr.Coefficient
	}

	return matrix
}

func (c *Correlator) FindCorrelatedGroups(series []model.TimeSeries, threshold float64) [][]string {
	if threshold == 0 {
		threshold = 0.5
	}

	corrMatrix := c.BuildCorrelationMatrix(series)
	visited := make(map[string]bool)
	var groups [][]string

	var dfs func(string, *[]string)
	dfs = func(metric string, group *[]string) {
		if visited[metric] {
			return
		}
		visited[metric] = true
		*group = append(*group, metric)

		for other, corr := range corrMatrix[metric] {
			if math.Abs(corr) >= threshold && !visited[other] {
				dfs(other, group)
			}
		}
	}

	for _, s := range series {
		if !visited[s.Name] {
			var group []string
			dfs(s.Name, &group)
			if len(group) > 0 {
				groups = append(groups, group)
			}
		}
	}

	return groups
}

func (c *Correlator) ComputeLaggedCorrelation(a, b model.TimeSeries, maxLag int) []model.CorrelationResult {
	dataA := extractSeriesValues(a)
	dataB := extractSeriesValues(b)

	var results []model.CorrelationResult

	for lag := -maxLag; lag <= maxLag; lag++ {
		alignedA, alignedB := lagSeries(dataA, dataB, lag)
		if len(alignedA) < 5 {
			continue
		}

		r, pValue := pearsonCorrelation(alignedA, alignedB)

		results = append(results, model.CorrelationResult{
			MetricA:     a.Name,
			MetricB:     b.Name,
			Coefficient: r,
			PValue:      pValue,
			Significant: pValue < c.significanceLevel,
		})
	}

	return results
}

func extractSeriesValues(ts model.TimeSeries) []float64 {
	values := make([]float64, len(ts.Points))
	for i, p := range ts.Points {
		values[i] = p.Value
	}
	return values
}

func lagSeries(a, b []float64, lag int) ([]float64, []float64) {
	if lag == 0 {
		minLen := min(len(a), len(b))
		return a[:minLen], b[:minLen]
	}

	if lag > 0 {
		if lag >= len(a) || lag >= len(b) {
			return nil, nil
		}
		minLen := min(len(a)-lag, len(b))
		return a[lag : lag+minLen], b[:minLen]
	}

	negLag := -lag
	if negLag >= len(a) || negLag >= len(b) {
		return nil, nil
	}
	minLen := min(len(a), len(b)-negLag)
	return a[:minLen], b[negLag : negLag+minLen]
}

func computePValue(r float64, n int) float64 {
	if n < 3 {
		return 1.0
	}
	if r >= 1.0 {
		return 0.0
	}
	if r <= -1.0 {
		return 0.0
	}

	t := r * math.Sqrt(float64(n-2)) / math.Sqrt(1-r*r)
	df := n - 2

	return 2 * tCDFTail(math.Abs(t), df)
}

func tCDFTail(t float64, df int) float64 {
	x := float64(df) / (float64(df) + t*t)
	return regularizedBetaP(x, float64(df)/2, 0.5)
}

func regularizedBetaP(x, a, b float64) float64 {
	if x <= 0 {
		return 0
	}
	if x >= 1 {
		return 1
	}

	bt := math.Exp(lgammaP(a)+lgammaP(b)-lgammaP(a+b)) *
		math.Pow(x, a) * math.Pow(1-x, b)

	if x < (a+1)/(a+b+2) {
		return bt * betaCFP(x, a, b) / a
	}
	return 1 - bt*betaCFP(1-x, b, a)/b
}

func betaCFP(x, a, b float64) float64 {
	maxIter := 200
	eps := 3.0e-7

	qab := a + b
	qap := a + 1
	qam := a - 1

	c := 1.0
	d := 1 - qab*x/qap
	if math.Abs(d) < 1e-30 {
		d = 1e-30
	}
	d = 1 / d
	h := d

	for m := 1; m <= maxIter; m++ {
		mf := float64(m)

		even := mf * (b - mf) * x / ((qam + 2*mf) * (a + 2*mf))
		d = 1 + even*d
		if math.Abs(d) < 1e-30 {
			d = 1e-30
		}
		c = 1 + even/c
		if math.Abs(c) < 1e-30 {
			c = 1e-30
		}
		d = 1 / d
		h *= d * c

		even = -(a + mf) * (qab + mf) * x / ((a + 2*mf) * (qap + 2*mf))
		d = 1 + even*d
		if math.Abs(d) < 1e-30 {
			d = 1e-30
		}
		c = 1 + even/c
		if math.Abs(c) < 1e-30 {
			c = 1e-30
		}
		d = 1 / d
		del := d * c
		h *= del

		if math.Abs(del-1) < eps {
			break
		}
	}

	return h
}

func lgammaP(x float64) float64 {
	coefficients := []float64{
		76.18009172947146,
		-86.50532032941677,
		24.01409824083091,
		-1.231739572450155,
		0.1208650973866179e-2,
		-0.5395239384953e-5,
	}

	y := x
	tmp := x + 5.5
	tmp -= (x + 0.5) * math.Log(tmp)
	ser := 1.000000000190015
	for _, c := range coefficients {
		y++
		ser += c / y
	}
	return -tmp + math.Log(2.5066282746310005*ser/x)
}

func pearsonCorrelation(x, y []float64) (float64, float64) {
	n := len(x)
	if n != len(y) || n < 3 {
		return 0, 1
	}

	meanX := 0.0
	meanY := 0.0
	for i := 0; i < n; i++ {
		meanX += x[i]
		meanY += y[i]
	}
	meanX /= float64(n)
	meanY /= float64(n)

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
		return 0, 1
	}

	r := covXY / math.Sqrt(varX*varY)

	t := r * math.Sqrt(float64(n-2)) / math.Sqrt(1-r*r)
	df := n - 2

	pValue := 2.0 * tCDFTail(math.Abs(t), df)

	return r, pValue
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
