package predict

import (
	"fmt"
	"math"
	"sync"
	"time"

	"autoscaler/internal/types"
)

type PredictionMethod string

const (
	MethodMovingAverage PredictionMethod = "ma"
	MethodWeightedMA    PredictionMethod = "wma"
	MethodExponential   PredictionMethod = "exponential"
	MethodARIMA         PredictionMethod = "arima"
)

type PredictorConfig struct {
	Method          PredictionMethod
	WindowSize      int
	Horizon         int
	Alpha           float64
	Seasonality     int
	Differencing    int
	AROrder         int
	MAOrder         int
	ErrorFeedback   types.ErrorFeedbackConfig
}

type Predictor struct {
	config     PredictorConfig
	errorState *types.ErrorFeedbackState
	mu         sync.RWMutex
}

func NewPredictor(config PredictorConfig) *Predictor {
	if config.Method == "" {
		config.Method = MethodExponential
	}
	if config.WindowSize == 0 {
		config.WindowSize = 10
	}
	if config.Horizon == 0 {
		config.Horizon = 5
	}
	if config.Alpha == 0 {
		config.Alpha = 0.3
	}
	if config.AROrder == 0 {
		config.AROrder = 2
	}
	if config.MAOrder == 0 {
		config.MAOrder = 1
	}

	if config.ErrorFeedback.WindowSize == 0 {
		config.ErrorFeedback.WindowSize = 50
	}
	if config.ErrorFeedback.MinSamples == 0 {
		config.ErrorFeedback.MinSamples = 10
	}
	if config.ErrorFeedback.MaxCorrection == 0 {
		config.ErrorFeedback.MaxCorrection = 20.0
	}
	if config.ErrorFeedback.UpdateInterval == 0 {
		config.ErrorFeedback.UpdateInterval = 5 * time.Minute
	}
	if config.ErrorFeedback.Alpha == 0 {
		config.ErrorFeedback.Alpha = 0.3
	}

	return &Predictor{
		config: config,
		errorState: &types.ErrorFeedbackState{
			Errors:      make([]types.PredictionError, 0),
			Corrections: make(map[types.MetricType]float64),
		},
	}
}

func (p *Predictor) Predict(data *types.MetricData) (float64, error) {
	if len(data.Values) < p.config.WindowSize {
		return 0, fmt.Errorf("insufficient data points: need %d, got %d", p.config.WindowSize, len(data.Values))
	}

	values := make([]float64, len(data.Values))
	for i, v := range data.Values {
		values[i] = v.Value
	}

	var prediction float64
	var err error

	switch p.config.Method {
	case MethodMovingAverage:
		prediction, err = p.movingAverage(values)
	case MethodWeightedMA:
		prediction, err = p.weightedMovingAverage(values)
	case MethodExponential:
		prediction, err = p.exponentialSmoothing(values)
	case MethodARIMA:
		prediction, err = p.arima(values)
	default:
		prediction, err = p.exponentialSmoothing(values)
	}

	if err != nil {
		return 0, err
	}

	data.Predicted = prediction

	if p.config.ErrorFeedback.Enabled {
		correction := p.errorState.GetCorrection(data.MetricType, p.config.ErrorFeedback)
		corrected := prediction + correction
		if corrected < 0 {
			corrected = 0
		}
		data.Corrected = corrected
		data.LastError = correction

		return corrected, nil
	}

	return prediction, nil
}

func (p *Predictor) movingAverage(values []float64) (float64, error) {
	n := len(values)
	if n < p.config.WindowSize {
		return 0, fmt.Errorf("not enough data for MA")
	}

	window := values[n-p.config.WindowSize:]
	sum := 0.0
	for _, v := range window {
		sum += v
	}

	return sum / float64(p.config.WindowSize), nil
}

func (p *Predictor) weightedMovingAverage(values []float64) (float64, error) {
	n := len(values)
	if n < p.config.WindowSize {
		return 0, fmt.Errorf("not enough data for WMA")
	}

	window := values[n-p.config.WindowSize:]
	weightedSum := 0.0
	weightTotal := 0

	for i, v := range window {
		weight := i + 1
		weightedSum += v * float64(weight)
		weightTotal += weight
	}

	return weightedSum / float64(weightTotal), nil
}

func (p *Predictor) exponentialSmoothing(values []float64) (float64, error) {
	if len(values) == 0 {
		return 0, fmt.Errorf("no data for exponential smoothing")
	}

	alpha := p.config.Alpha
	prediction := values[0]

	for i := 1; i < len(values); i++ {
		prediction = alpha*values[i] + (1-alpha)*prediction
	}

	trend := 0.0
	if len(values) >= 2 {
		trend = (values[len(values)-1] - values[len(values)-2])
	}

	return prediction + trend*float64(p.config.Horizon), nil
}

func (p *Predictor) arima(values []float64) (float64, error) {
	d := p.config.Differencing
	diffSeries := make([]float64, len(values))
	copy(diffSeries, values)

	for i := 0; i < d; i++ {
		if len(diffSeries) < 2 {
			return 0, fmt.Errorf("series too short for differencing")
		}
		diffed := make([]float64, len(diffSeries)-1)
		for j := 1; j < len(diffSeries); j++ {
			diffed[j-1] = diffSeries[j] - diffSeries[j-1]
		}
		diffSeries = diffed
	}

	arParams, err := p.estimateAR(diffSeries, p.config.AROrder)
	if err != nil {
		return 0, err
	}

	maParams, residuals := p.estimateMA(diffSeries, arParams, p.config.MAOrder)

	predictedDiff := 0.0
	for i := 0; i < p.config.AROrder; i++ {
		idx := len(diffSeries) - 1 - i
		if idx >= 0 {
			predictedDiff += arParams[i] * diffSeries[idx]
		}
	}

	for i := 0; i < p.config.MAOrder; i++ {
		idx := len(residuals) - 1 - i
		if idx >= 0 {
			predictedDiff += maParams[i] * residuals[idx]
		}
	}

	prediction := predictedDiff
	lastIdx := len(values) - 1
	for i := 0; i < d; i++ {
		prediction += values[lastIdx-i]
	}

	return prediction, nil
}

func (p *Predictor) estimateAR(series []float64, order int) ([]float64, error) {
	n := len(series)
	if n < order*2 {
		return nil, fmt.Errorf("series too short for AR estimation")
	}

	X := make([][]float64, n-order)
	Y := make([]float64, n-order)

	for i := 0; i < n-order; i++ {
		X[i] = make([]float64, order)
		for j := 0; j < order; j++ {
			X[i][j] = series[i+j]
		}
		Y[i] = series[i+order]
	}

	params := make([]float64, order)
	for j := 0; j < order; j++ {
		sumXY := 0.0
		sumX2 := 0.0
		for i := 0; i < len(X); i++ {
			sumXY += X[i][j] * Y[i]
			sumX2 += X[i][j] * X[i][j]
		}
		if sumX2 > 0 {
			params[j] = sumXY / sumX2
		}
	}

	return params, nil
}

func (p *Predictor) estimateMA(series []float64, arParams []float64, order int) ([]float64, []float64) {
	n := len(series)
	residuals := make([]float64, n)

	for i := 0; i < n; i++ {
		pred := 0.0
		for j := 0; j < len(arParams) && i-j-1 >= 0; j++ {
			pred += arParams[j] * series[i-j-1]
		}
		residuals[i] = series[i] - pred
	}

	maParams := make([]float64, order)
	if len(residuals) < order+1 {
		return maParams, residuals
	}

	for j := 0; j < order; j++ {
		sumRE := 0.0
		sumR2 := 0.0
		for i := order; i < len(residuals); i++ {
			sumRE += residuals[i-j-1] * residuals[i]
			sumR2 += residuals[i-j-1] * residuals[i-j-1]
		}
		if sumR2 > 0 {
			maParams[j] = sumRE / sumR2
		}
	}

	return maParams, residuals
}

func (p *Predictor) PredictWithTrend(data *types.MetricData) (float64, float64, error) {
	prediction, err := p.Predict(data)
	if err != nil {
		return 0, 0, err
	}

	values := make([]float64, len(data.Values))
	for i, v := range data.Values {
		values[i] = v.Value
	}

	trend := 0.0
	if len(values) >= 2 {
		recentN := int(math.Min(float64(p.config.WindowSize), float64(len(values)-1)))
		older := values[len(values)-recentN-1]
		newer := values[len(values)-1]
		trend = (newer - older) / float64(recentN)
	}

	interval := time.Duration(0)
	if len(data.Values) >= 2 {
		interval = data.Values[1].Timestamp.Sub(data.Values[0].Timestamp)
	}
	futureValue := prediction + trend*float64(p.config.Horizon)*float64(interval/time.Minute)

	return prediction, futureValue, nil
}

func (p *Predictor) GetConfidenceInterval(data *types.MetricData, prediction float64) (float64, float64, error) {
	if len(data.Values) < 2 {
		return 0, 0, fmt.Errorf("not enough data for confidence interval")
	}

	values := make([]float64, len(data.Values))
	for i, v := range data.Values {
		values[i] = v.Value
	}

	mean := 0.0
	for _, v := range values {
		mean += v
	}
	mean /= float64(len(values))

	variance := 0.0
	for _, v := range values {
		variance += (v - mean) * (v - mean)
	}
	variance /= float64(len(values) - 1)

	stdDev := math.Sqrt(variance)
	margin := 1.96 * stdDev / math.Sqrt(float64(len(values)))

	return prediction - margin, prediction + margin, nil
}

func (p *Predictor) RecordError(metricType types.MetricType, predicted, actual float64) {
	error := actual - predicted
	errorRatio := 0.0
	if actual != 0 {
		errorRatio = error / actual * 100
	}

	err := types.PredictionError{
		MetricType: metricType,
		Timestamp:  time.Now(),
		Predicted:  predicted,
		Actual:     actual,
		Error:      error,
		ErrorRatio: errorRatio,
	}

	p.mu.Lock()
	p.errorState.RecordError(err)
	p.mu.Unlock()
}

func (p *Predictor) UpdateCorrections() {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.errorState.UpdateCorrections(p.config.ErrorFeedback)
}

func (p *Predictor) GetCorrection(metricType types.MetricType) float64 {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.errorState.GetCorrection(metricType, p.config.ErrorFeedback)
}

func (p *Predictor) GetErrorState() *types.ErrorFeedbackState {
	p.mu.RLock()
	defer p.mu.RUnlock()
	return p.errorState
}
