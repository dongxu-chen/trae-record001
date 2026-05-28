package analyzer

import (
	"math"
	"time"

	"container-autoscaler/pkg/types"
	"container-autoscaler/pkg/utils"
)

type RegressionAnalyzer struct {
	logger *utils.Logger
}

func NewRegressionAnalyzer(logger *utils.Logger) *RegressionAnalyzer {
	return &RegressionAnalyzer{
		logger: logger,
	}
}

func (r *RegressionAnalyzer) PolynomialRegression(
	ts types.TimeSeriesData,
	degree int,
) ([]float64, float64) {
	cleaned := RemoveOutliers3Sigma(ts.Values)
	n := len(cleaned)
	if n <= degree {
		return nil, 0
	}

	x := make([]float64, n)
	for i := range x {
		x[i] = float64(i)
	}

	coefficients := solvePolynomial(x, cleaned, degree)

	predicted := make([]float64, n)
	for i := range x {
		predicted[i] = evaluatePolynomial(coefficients, x[i])
	}

	r2 := calculateR2(cleaned, predicted)

	return coefficients, r2
}

func (r *RegressionAnalyzer) ExponentialRegression(
	ts types.TimeSeriesData,
) (types.RegressionResult, float64) {
	cleaned := RemoveOutliers3Sigma(ts.Values)
	n := len(cleaned)
	if n < 2 {
		return types.RegressionResult{}, 0
	}

	hasNegative := false
	for _, v := range cleaned {
		if v <= 0 {
			hasNegative = true
			break
		}
	}

	if hasNegative {
		minVal := math.Inf(1)
		for _, v := range cleaned {
			if v < minVal && v > 0 {
				minVal = v
			}
		}
		shift := math.Abs(minVal) + 1

		shifted := make([]float64, n)
		for i, v := range cleaned {
			shifted[i] = v + shift
		}

		result := linearRegressionLog(shifted)
		result.Intercept -= shift
		return result, result.R2
	}

	return linearRegressionLog(cleaned)
}

func RemoveOutliers3Sigma(values []float64) []float64 {
	n := len(values)
	if n < 10 {
		return values
	}

	m := 0.0
	for _, v := range values {
		m += v
	}
	m /= float64(n)

	s := 0.0
	for _, v := range values {
		s += (v - m) * (v - m)
	}
	s = math.Sqrt(s / float64(n))

	if s == 0 {
		return values
	}

	lower := m - 3*s
	upper := m + 3*s

	result := make([]float64, 0, n)
	removedCount := 0
	for _, v := range values {
		if v >= lower && v <= upper {
			result = append(result, v)
		} else {
			removedCount++
		}
	}

	if removedCount > 0 && len(result) > 0 {
		return result
	}

	return values
}

func RemoveOutliers3SigmaTS(ts types.TimeSeriesData) types.TimeSeriesData {
	n := len(ts.Values)
	if n < 10 {
		return ts
	}

	m := 0.0
	for _, v := range ts.Values {
		m += v
	}
	m /= float64(n)

	s := 0.0
	for _, v := range ts.Values {
		s += (v - m) * (v - m)
	}
	s = math.Sqrt(s / float64(n))

	if s == 0 {
		return ts
	}

	lower := m - 3*s
	upper := m + 3*s

	result := types.TimeSeriesData{
		Timestamps: make([]time.Time, 0, n),
		Values:     make([]float64, 0, n),
	}

	removedCount := 0
	for i, v := range ts.Values {
		if v >= lower && v <= upper {
			result.Values = append(result.Values, v)
			result.Timestamps = append(result.Timestamps, ts.Timestamps[i])
		} else {
			removedCount++
		}
	}

	if removedCount > 0 && len(result.Values) > 0 {
		return result
	}

	return ts
}

func linearRegressionLog(values []float64) types.RegressionResult {
	n := len(values)

	logValues := make([]float64, n)
	for i, v := range values {
		logValues[i] = math.Log(v)
	}

	x := make([]float64, n)
	for i := range x {
		x[i] = float64(i)
	}

	sumX := 0.0
	sumY := 0.0
	sumXY := 0.0
	sumX2 := 0.0

	for i := 0; i < n; i++ {
		sumX += x[i]
		sumY += logValues[i]
		sumXY += x[i] * logValues[i]
		sumX2 += x[i] * x[i]
	}

	denominator := float64(n)*sumX2 - sumX*sumX
	if denominator == 0 {
		return types.RegressionResult{}
	}

	logSlope := (float64(n)*sumXY - sumX*sumY) / denominator
	logIntercept := (sumY - logSlope*sumX) / float64(n)

	a := math.Exp(logIntercept)
	b := logSlope

	predicted := make([]float64, n)
	for i := 0; i < n; i++ {
		predicted[i] = a * math.Exp(b*x[i])
	}

	meanY := 0.0
	for _, v := range values {
		meanY += v
	}
	meanY /= float64(n)

	ssTotal := 0.0
	ssResidual := 0.0
	for i := 0; i < n; i++ {
		ssResidual += math.Pow(values[i]-predicted[i], 2)
		ssTotal += math.Pow(values[i]-meanY, 2)
	}

	r2 := 0.0
	if ssTotal > 0 {
		r2 = 1 - ssResidual/ssTotal
	}

	return types.RegressionResult{
		Slope:      b,
		Intercept:  a,
		R2:         r2,
		Confidence: math.Abs(r2),
	}
}

func (r *RegressionAnalyzer) MultipleRegression(
	tsList []types.TimeSeriesData,
	weights []float64,
) types.TimeSeriesData {
	if len(tsList) == 0 {
		return types.TimeSeriesData{}
	}

	n := len(tsList[0].Values)
	for _, ts := range tsList {
		if len(ts.Values) < n {
			n = len(ts.Values)
		}
	}

	result := types.TimeSeriesData{
		Timestamps: make([]time.Time, n),
		Values:     make([]float64, n),
	}

	totalWeight := 0.0
	for _, w := range weights {
		totalWeight += w
	}

	for i := 0; i < n; i++ {
		weightedSum := 0.0
		for j, ts := range tsList {
			w := weights[j] / totalWeight
			weightedSum += ts.Values[i] * w
		}
		result.Values[i] = weightedSum
		result.Timestamps[i] = tsList[0].Timestamps[i]
	}

	return result
}

func (r *RegressionAnalyzer) AutoregressiveModel(
	ts types.TimeSeriesData,
	order int,
) (func(int) float64, float64) {
	cleanedTS := RemoveOutliers3SigmaTS(ts)
	n := len(cleanedTS.Values)
	if n <= order {
		return func(int) float64 { return 0 }, 0
	}

	trainData := cleanedTS.Values[:n-order]
	if len(trainData) <= order {
		return func(int) float64 { return 0 }, 0
	}

	x := make([][]float64, len(trainData)-order)
	y := make([]float64, len(trainData)-order)

	for i := order; i < len(trainData); i++ {
		x[i-order] = make([]float64, order)
		for j := 0; j < order; j++ {
			x[i-order][j] = trainData[i-order+j]
		}
		y[i-order] = trainData[i]
	}

	coefficients := solveLinearSystem(x, y)
	if coefficients == nil {
		return func(int) float64 { return 0 }, 0
	}

	predictor := func(steps int) float64 {
		history := make([]float64, order)
		copy(history, cleanedTS.Values[n-order:])

		for i := 0; i < steps; i++ {
			pred := 0.0
			for j, c := range coefficients {
				pred += c * history[j]
			}

			for j := 0; j < order-1; j++ {
				history[j] = history[j+1]
			}
			history[order-1] = pred
		}

		return history[order-1]
	}

	predicted := make([]float64, len(y))
	for i := range y {
		pred := 0.0
		for j, c := range coefficients {
			pred += c * x[i][j]
		}
		predicted[i] = pred
	}

	r2 := calculateR2(y, predicted)

	return predictor, r2
}

func solvePolynomial(x, y []float64, degree int) []float64 {
	n := len(x)
	m := degree + 1

	a := make([][]float64, m)
	for i := range a {
		a[i] = make([]float64, m)
	}

	b := make([]float64, m)

	for i := 0; i < m; i++ {
		for j := 0; j < m; j++ {
			sum := 0.0
			for k := 0; k < n; k++ {
				sum += math.Pow(x[k], float64(i+j))
			}
			a[i][j] = sum
		}

		sum := 0.0
		for k := 0; k < n; k++ {
			sum += y[k] * math.Pow(x[k], float64(i))
		}
		b[i] = sum
	}

	return gaussianElimination(a, b)
}

func evaluatePolynomial(coefficients []float64, x float64) float64 {
	result := 0.0
	for i, c := range coefficients {
		result += c * math.Pow(x, float64(i))
	}
	return result
}

func solveLinearSystem(x [][]float64, y []float64) []float64 {
	n := len(x)
	if n == 0 {
		return nil
	}

	m := len(x[0])

	a := make([][]float64, m)
	for i := range a {
		a[i] = make([]float64, m)
	}

	b := make([]float64, m)

	for i := 0; i < m; i++ {
		for j := 0; j < m; j++ {
			sum := 0.0
			for k := 0; k < n; k++ {
				sum += x[k][i] * x[k][j]
			}
			a[i][j] = sum
		}

		sum := 0.0
		for k := 0; k < n; k++ {
			sum += x[k][i] * y[k]
		}
		b[i] = sum
	}

	return gaussianElimination(a, b)
}

func gaussianElimination(a [][]float64, b []float64) []float64 {
	n := len(a)

	augmented := make([][]float64, n)
	for i := range augmented {
		augmented[i] = make([]float64, n+1)
		copy(augmented[i][:n], a[i])
		augmented[i][n] = b[i]
	}

	for col := 0; col < n; col++ {
		maxRow := col
		for row := col + 1; row < n; row++ {
			if math.Abs(augmented[row][col]) > math.Abs(augmented[maxRow][col]) {
				maxRow = row
			}
		}
		augmented[col], augmented[maxRow] = augmented[maxRow], augmented[col]

		if math.Abs(augmented[col][col]) < 1e-10 {
			return nil
		}

		for row := col + 1; row < n; row++ {
			factor := augmented[row][col] / augmented[col][col]
			for j := col; j <= n; j++ {
				augmented[row][j] -= factor * augmented[col][j]
			}
		}
	}

	result := make([]float64, n)
	for i := n - 1; i >= 0; i-- {
		sum := augmented[i][n]
		for j := i + 1; j < n; j++ {
			sum -= augmented[i][j] * result[j]
		}
		result[i] = sum / augmented[i][i]
	}

	return result
}

func calculateR2(actual, predicted []float64) float64 {
	n := len(actual)
	if n == 0 {
		return 0
	}

	meanY := 0.0
	for _, v := range actual {
		meanY += v
	}
	meanY /= float64(n)

	ssTotal := 0.0
	ssResidual := 0.0
	for i := 0; i < n; i++ {
		ssResidual += math.Pow(actual[i]-predicted[i], 2)
		ssTotal += math.Pow(actual[i]-meanY, 2)
	}

	if ssTotal == 0 {
		return 1
	}

	return 1 - ssResidual/ssTotal
}
