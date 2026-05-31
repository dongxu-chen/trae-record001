package predictor

import (
	"math"
	"sort"
	"time"
)

type TimeSeriesPoint struct {
	Timestamp time.Time `json:"timestamp"`
	Value     float64   `json:"value"`
}

type PeriodicPattern struct {
	Period    time.Duration `json:"period"`
	Amplitude float64       `json:"amplitude"`
	Phase     float64       `json:"phase"`
	Strength  float64       `json:"strength"`
}

type FourierComponent struct {
	Frequency float64 `json:"frequency"`
	Amplitude float64 `json:"amplitude"`
	Phase     float64 `json:"phase"`
}

type PredictionResult struct {
	PredictedValues   []TimeSeriesPoint  `json:"predictedValues"`
	Algorithm         string             `json:"algorithm"`
	Confidence        float64            `json:"confidence"`
	MSE               float64            `json:"mse"`
	DetectedPatterns  []PeriodicPattern  `json:"detectedPatterns,omitempty"`
	FourierComponents []FourierComponent `json:"fourierComponents,omitempty"`
}

type PredictionEngine struct {
	windowSize    int
	forecastSteps int
}

func NewPredictionEngine(windowSize int) *PredictionEngine {
	return &PredictionEngine{
		windowSize:    windowSize,
		forecastSteps: windowSize,
	}
}

func (e *PredictionEngine) MovingAverage(data []TimeSeriesPoint, window int) []TimeSeriesPoint {
	result := make([]TimeSeriesPoint, len(data))
	for i := 0; i < len(data); i++ {
		sum := 0.0
		count := 0
		start := i - window + 1
		if start < 0 {
			start = 0
		}
		for j := start; j <= i; j++ {
			sum += data[j].Value
			count++
		}
		result[i] = TimeSeriesPoint{
			Timestamp: data[i].Timestamp,
			Value:     sum / float64(count),
		}
	}
	return result
}

func (e *PredictionEngine) ExponentialSmoothing(data []TimeSeriesPoint, alpha float64) PredictionResult {
	if len(data) == 0 {
		return PredictionResult{Algorithm: "ExponentialSmoothing"}
	}

	smoothed := make([]float64, len(data))
	smoothed[0] = data[0].Value
	for i := 1; i < len(data); i++ {
		smoothed[i] = alpha*data[i].Value + (1-alpha)*smoothed[i-1]
	}

	steps := e.forecastSteps
	if steps <= 0 {
		steps = 1
	}
	lastTime := data[len(data)-1].Timestamp
	interval := avgInterval(data)
	lastLevel := smoothed[len(data)-1]

	predicted := make([]TimeSeriesPoint, steps)
	for i := 0; i < steps; i++ {
		predicted[i] = TimeSeriesPoint{
			Timestamp: lastTime.Add(interval * time.Duration(i+1)),
			Value:     lastLevel,
		}
	}

	mse := calcMSE(data, smoothed)
	return PredictionResult{
		PredictedValues: predicted,
		Algorithm:       "ExponentialSmoothing",
		Confidence:      1.0 / (1.0 + mse),
		MSE:             mse,
	}
}

func (e *PredictionEngine) DoubleExponentialSmoothing(data []TimeSeriesPoint, alpha, beta float64) PredictionResult {
	if len(data) < 2 {
		return PredictionResult{Algorithm: "DoubleExponentialSmoothing"}
	}

	n := len(data)
	level := make([]float64, n)
	trend := make([]float64, n)
	fitted := make([]float64, n)

	level[0] = data[0].Value
	trend[0] = data[1].Value - data[0].Value
	fitted[0] = level[0]

	for i := 1; i < n; i++ {
		level[i] = alpha*data[i].Value + (1-alpha)*(level[i-1]+trend[i-1])
		trend[i] = beta*(level[i]-level[i-1]) + (1-beta)*trend[i-1]
		fitted[i] = level[i-1] + trend[i-1]
	}

	steps := e.forecastSteps
	if steps <= 0 {
		steps = 1
	}
	lastTime := data[n-1].Timestamp
	interval := avgInterval(data)
	lastLevel := level[n-1]
	lastTrend := trend[n-1]

	predicted := make([]TimeSeriesPoint, steps)
	for i := 0; i < steps; i++ {
		predicted[i] = TimeSeriesPoint{
			Timestamp: lastTime.Add(interval * time.Duration(i+1)),
			Value:     lastLevel + float64(i+1)*lastTrend,
		}
	}

	mse := calcMSE(data, fitted)
	return PredictionResult{
		PredictedValues: predicted,
		Algorithm:       "DoubleExponentialSmoothing",
		Confidence:      1.0 / (1.0 + mse),
		MSE:             mse,
	}
}

func (e *PredictionEngine) LinearRegression(data []TimeSeriesPoint) PredictionResult {
	if len(data) < 2 {
		return PredictionResult{Algorithm: "LinearRegression"}
	}

	n := len(data)
	var sumX, sumY, sumXY, sumX2 float64
	for i := 0; i < n; i++ {
		x := float64(i)
		y := data[i].Value
		sumX += x
		sumY += y
		sumXY += x * y
		sumX2 += x * x
	}

	denom := float64(n)*sumX2 - sumX*sumX
	slope := (float64(n)*sumXY - sumX*sumY) / denom
	intercept := (sumY - slope*sumX) / float64(n)

	fitted := make([]float64, n)
	for i := 0; i < n; i++ {
		fitted[i] = intercept + slope*float64(i)
	}

	steps := e.forecastSteps
	if steps <= 0 {
		steps = 1
	}
	lastTime := data[n-1].Timestamp
	interval := avgInterval(data)

	predicted := make([]TimeSeriesPoint, steps)
	for i := 0; i < steps; i++ {
		predicted[i] = TimeSeriesPoint{
			Timestamp: lastTime.Add(interval * time.Duration(i+1)),
			Value:     intercept + slope*float64(n+i),
		}
	}

	mse := calcMSE(data, fitted)
	return PredictionResult{
		PredictedValues: predicted,
		Algorithm:       "LinearRegression",
		Confidence:      1.0 / (1.0 + mse),
		MSE:             mse,
	}
}

func (e *PredictionEngine) DetectPeriodicity(data []TimeSeriesPoint) []PeriodicPattern {
	n := len(data)
	if n < 4 {
		return nil
	}

	interval := avgInterval(data)
	intervalSec := interval.Seconds()

	candidates := []time.Duration{
		time.Hour,
		6 * time.Hour,
		12 * time.Hour,
		24 * time.Hour,
		7 * 24 * time.Hour,
	}

	var patterns []PeriodicPattern
	values := make([]float64, n)
	for i := 0; i < n; i++ {
		values[i] = data[i].Value
	}

	var mean float64
	for _, v := range values {
		mean += v
	}
	mean /= float64(n)

	for _, period := range candidates {
		periodSec := period.Seconds()
		lag := int(periodSec / intervalSec)
		if lag < 1 || lag >= n {
			continue
		}

		var num, den1, den2 float64
		for i := 0; i < n-lag; i++ {
			xi := values[i] - mean
			yi := values[i+lag] - mean
			num += xi * yi
			den1 += xi * xi
			den2 += yi * yi
		}

		den := math.Sqrt(den1 * den2)
		if den == 0 {
			continue
		}
		correlation := num / den

		if correlation > 0.6 {
			var maxV, minV float64 = values[0], values[0]
			for _, v := range values {
				if v > maxV {
					maxV = v
				}
				if v < minV {
					minV = v
				}
			}
			amplitude := (maxV - minV) / 2

			peakIdx := 0
			for i := 0; i < lag && i < n; i++ {
				if values[i] > values[peakIdx] {
					peakIdx = i
				}
			}
			phase := float64(peakIdx) / float64(lag) * 2 * math.Pi

			patterns = append(patterns, PeriodicPattern{
				Period:    period,
				Amplitude: amplitude,
				Phase:     phase,
				Strength:  correlation,
			})
		}
	}

	sort.Slice(patterns, func(i, j int) bool {
		return patterns[i].Strength > patterns[j].Strength
	})

	return patterns
}

func (e *PredictionEngine) FastFourierTransform(data []TimeSeriesPoint) []FourierComponent {
	n := len(data)
	if n < 2 {
		return nil
	}

	values := make([]float64, n)
	for i := 0; i < n; i++ {
		values[i] = data[i].Value
	}

	var mean float64
	for _, v := range values {
		mean += v
	}
	mean /= float64(n)
	for i := 0; i < n; i++ {
		values[i] -= mean
	}

	components := make([]FourierComponent, 0, n/2)
	for k := 1; k <= n/2; k++ {
		var re, im float64
		for i := 0; i < n; i++ {
			angle := -2 * math.Pi * float64(k) * float64(i) / float64(n)
			re += values[i] * math.Cos(angle)
			im += values[i] * math.Sin(angle)
		}
		amplitude := math.Sqrt(re*re+im*im) * 2 / float64(n)
		phase := math.Atan2(im, re)
		interval := avgInterval(data)
		frequency := 1.0 / (interval.Seconds() * float64(n) / float64(k))

		components = append(components, FourierComponent{
			Frequency: frequency,
			Amplitude: amplitude,
			Phase:     phase,
		})
	}

	sort.Slice(components, func(i, j int) bool {
		return components[i].Amplitude > components[j].Amplitude
	})

	if len(components) > 5 {
		components = components[:5]
	}

	return components
}

func (e *PredictionEngine) PredictWithPeriodicity(data []TimeSeriesPoint, steps int) PredictionResult {
	if len(data) < 2 {
		return PredictionResult{Algorithm: "PeriodicForecast"}
	}

	patterns := e.DetectPeriodicity(data)
	fourier := e.FastFourierTransform(data)
	trendResult := e.DoubleExponentialSmoothing(data, 0.3, 0.1)

	n := len(data)
	interval := avgInterval(data)
	intervalSec := interval.Seconds()
	lastTime := data[n-1].Timestamp

	predicted := make([]TimeSeriesPoint, steps)
	for i := 0; i < steps; i++ {
		t := float64(n + i)
		trendValue := trendResult.PredictedValues[i].Value

		var periodicSum float64
		for _, p := range patterns {
			periodSec := p.Period.Seconds()
			periodSteps := periodSec / intervalSec
			periodicSum += p.Amplitude * math.Sin(2*math.Pi*(t+p.Phase/(2*math.Pi)*periodSteps)/periodSteps)
		}

		predicted[i] = TimeSeriesPoint{
			Timestamp: lastTime.Add(interval * time.Duration(i+1)),
			Value:     trendValue + periodicSum,
		}
	}

	var mean float64
	for _, d := range data {
		mean += d.Value
	}
	mean /= float64(n)

	fitted := make([]float64, n)
	for i := 0; i < n; i++ {
		t := float64(i)
		var periodicSum float64
		for _, p := range patterns {
			periodSec := p.Period.Seconds()
			periodSteps := periodSec / intervalSec
			periodicSum += p.Amplitude * math.Sin(2*math.Pi*(t+p.Phase/(2*math.Pi)*periodSteps)/periodSteps)
		}
		fitted[i] = mean + periodicSum
	}

	mse := calcMSE(data, fitted)

	return PredictionResult{
		PredictedValues:   predicted,
		Algorithm:         "PeriodicForecast",
		Confidence:        1.0 / (1.0 + mse),
		MSE:               mse,
		DetectedPatterns:  patterns,
		FourierComponents: fourier,
	}
}

func (e *PredictionEngine) Predict(data []TimeSeriesPoint, steps int) []PredictionResult {
	e.forecastSteps = steps

	var results []PredictionResult

	results = append(results, e.ExponentialSmoothing(data, 0.3))
	results = append(results, e.DoubleExponentialSmoothing(data, 0.3, 0.1))
	results = append(results, e.LinearRegression(data))

	if len(data) > 0 {
		ma := e.MovingAverage(data, e.windowSize)
		n := len(data)
		lastMAValue := ma[n-1].Value
		lastTime := data[n-1].Timestamp
		interval := avgInterval(data)

		predictedMA := make([]TimeSeriesPoint, steps)
		for i := 0; i < steps; i++ {
			predictedMA[i] = TimeSeriesPoint{
				Timestamp: lastTime.Add(interval * time.Duration(i+1)),
				Value:     lastMAValue,
			}
		}

		fittedMA := make([]float64, n)
		for i := 0; i < n; i++ {
			fittedMA[i] = ma[i].Value
		}
		mseMA := calcMSE(data, fittedMA)

		results = append(results, PredictionResult{
			PredictedValues: predictedMA,
			Algorithm:       "MovingAverage",
			Confidence:      1.0 / (1.0 + mseMA),
			MSE:             mseMA,
		})
	}

	results = append(results, e.PredictWithPeriodicity(data, steps))

	return results
}

func (e *PredictionEngine) WeightedEnsemble(results []PredictionResult, weights []float64) PredictionResult {
	if len(results) == 0 {
		return PredictionResult{Algorithm: "WeightedEnsemble"}
	}

	minLen := len(results[0].PredictedValues)
	for _, r := range results[1:] {
		if len(r.PredictedValues) < minLen {
			minLen = len(r.PredictedValues)
		}
	}

	predicted := make([]TimeSeriesPoint, minLen)
	for i := 0; i < minLen; i++ {
		var wSum float64
		var wTotal float64
		var ts time.Time
		for j := 0; j < len(results) && j < len(weights); j++ {
			if i < len(results[j].PredictedValues) {
				wSum += weights[j] * results[j].PredictedValues[i].Value
				wTotal += weights[j]
				ts = results[j].PredictedValues[i].Timestamp
			}
		}
		if wTotal > 0 {
			predicted[i] = TimeSeriesPoint{
				Timestamp: ts,
				Value:     wSum / wTotal,
			}
		}
	}

	var wConf, wMSE, wSum float64
	for j := 0; j < len(results) && j < len(weights); j++ {
		wConf += weights[j] * results[j].Confidence
		wMSE += weights[j] * results[j].MSE
		wSum += weights[j]
	}

	var confidence, mse float64
	if wSum > 0 {
		confidence = wConf / wSum
		mse = wMSE / wSum
	}

	return PredictionResult{
		PredictedValues: predicted,
		Algorithm:       "WeightedEnsemble",
		Confidence:      confidence,
		MSE:             mse,
	}
}

func avgInterval(data []TimeSeriesPoint) time.Duration {
	if len(data) < 2 {
		return time.Hour
	}
	return data[len(data)-1].Timestamp.Sub(data[0].Timestamp) / time.Duration(len(data)-1)
}

func calcMSE(data []TimeSeriesPoint, fitted []float64) float64 {
	n := len(data)
	if n == 0 || len(fitted) == 0 {
		return 0
	}

	portion := n / 5
	if portion < 1 {
		portion = 1
	}
	start := n - portion

	var sum float64
	count := 0
	for i := start; i < n && i < len(fitted); i++ {
		diff := data[i].Value - fitted[i]
		sum += diff * diff
		count++
	}
	if count == 0 {
		return 0
	}
	return sum / float64(count)
}
