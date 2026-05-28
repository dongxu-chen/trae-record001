package predictor

import (
	"fmt"
	"math"
	"strings"
	"time"

	"container-autoscaler/pkg/config"
	"container-autoscaler/pkg/types"
	"container-autoscaler/pkg/utils"
)

type TimeSeriesPredictor struct {
	config config.PredictionConfig
	logger *utils.Logger
}

type CyclicPattern struct {
	Period          int
	Amplitude       float64
	Phase           float64
	Strength        float64
	Confidence      float64
	PeakHours       []int
	TroughHours     []int
}

func NewTimeSeriesPredictor(cfg config.PredictionConfig, logger *utils.Logger) *TimeSeriesPredictor {
	return &TimeSeriesPredictor{
		config: cfg,
		logger: logger,
	}
}

func (p *TimeSeriesPredictor) DetectCyclicPatterns(
	ts types.TimeSeriesData,
) []CyclicPattern {
	n := len(ts.Values)
	if n < p.config.SeasonalPeriod*2 {
		p.logger.Debug("Insufficient data for cyclic pattern detection, need at least %d points",
			p.config.SeasonalPeriod*2)
		return nil
	}

	patterns := make([]CyclicPattern, 0)

	candidatePeriods := p.config.CyclicPeriods
	if len(candidatePeriods) == 0 {
		candidatePeriods = []int{12, 24, 48, 96, 168, 336}
	}

	autocorr := p.calculateAutocorrelation(ts.Values)

	for _, period := range candidatePeriods {
		if period >= n {
			continue
		}

		strength := 0.0
		if period < len(autocorr) {
			strength = math.Abs(autocorr[period])
		}

		if strength < 0.15 {
			continue
		}

		pattern := CyclicPattern{
			Period:     period,
			Strength:   strength,
			Confidence: strength,
		}

		freq := 2.0 * math.Pi / float64(period)
		sumSin := 0.0
		sumCos := 0.0
		for i, v := range ts.Values {
			t := float64(i)
			sumSin += v * math.Sin(freq*t)
			sumCos += v * math.Cos(freq*t)
		}
		sumSin /= float64(n)
		sumCos /= float64(n)

		pattern.Amplitude = 2.0 * math.Sqrt(sumSin*sumSin+sumCos*sumCos)
		pattern.Phase = math.Atan2(sumSin, sumCos)

		pattern.PeakHours, pattern.TroughHours = p.detectPeaksAndTroughs(ts, period)

		patterns = append(patterns, pattern)
	}

	return patterns
}

func (p *TimeSeriesPredictor) calculateAutocorrelation(values []float64) []float64 {
	n := len(values)
	mean := 0.0
	for _, v := range values {
		mean += v
	}
	mean /= float64(n)

	variance := 0.0
	for _, v := range values {
		variance += (v - mean) * (v - mean)
	}
	variance /= float64(n)

	if variance == 0 {
		return make([]float64, n)
	}

	maxLag := n / 4
	if maxLag < 10 {
		maxLag = 10
	}
	if maxLag > n {
		maxLag = n
	}

	autocorr := make([]float64, maxLag)
	for lag := 0; lag < maxLag; lag++ {
		sum := 0.0
		for i := 0; i < n-lag; i++ {
			sum += (values[i] - mean) * (values[i+lag] - mean)
		}
		autocorr[lag] = sum / (float64(n-lag) * variance)
	}

	return autocorr
}

func (p *TimeSeriesPredictor) detectPeaksAndTroughs(
	ts types.TimeSeriesData,
	period int,
) ([]int, []int) {
	n := len(ts.Values)
	if n < period*2 {
		return nil, nil
	}

	phaseValues := make([][]float64, period)
	for i := range phaseValues {
		phaseValues[i] = make([]float64, 0)
	}

	for i, v := range ts.Values {
		phase := i % period
		phaseValues[phase] = append(phaseValues[phase], v)
	}

	phaseMeans := make([]float64, period)
	for i, vals := range phaseValues {
		if len(vals) == 0 {
			phaseMeans[i] = 0
			continue
		}
		sum := 0.0
		for _, v := range vals {
			sum += v
		}
		phaseMeans[i] = sum / float64(len(vals))
	}

	overallMean := 0.0
	for _, v := range phaseMeans {
		overallMean += v
	}
	overallMean /= float64(period)

	peakHours := make([]int, 0)
	troughHours := make([]int, 0)

	threshold := 0.1
	for i, v := range phaseMeans {
		if overallMean > 0 {
			deviation := (v - overallMean) / overallMean
			if deviation > threshold {
				peakHours = append(peakHours, i)
			} else if deviation < -threshold {
				troughHours = append(troughHours, i)
		}
		}
	}

	return peakHours, troughHours
}

func (p *TimeSeriesPredictor) FourierPrediction(
	ts types.TimeSeriesData,
	predictionSteps int,
	patterns []CyclicPattern,
) (float64, float64, error) {
	n := len(ts.Values)
	if n == 0 {
		return 0, 0, fmt.Errorf("empty time series")
	}

	if len(patterns) == 0 {
		return 0, 0, fmt.Errorf("no cyclic patterns detected")
	}

	baseValue := 0.0
	for _, v := range ts.Values {
		baseValue += v
	}
	baseValue /= float64(n)

	trendSlope := 0.0
	if n > 1 {
		trendSlope = (ts.Values[n-1] - ts.Values[0]) / float64(n-1)
	}

	futureIndex := n + predictionSteps - 1
	predicted := baseValue + float64(predictionSteps)*trendSlope

	totalWeight := 0.0
	for _, pattern := range patterns {
		freq := 2.0 * math.Pi / float64(pattern.Period)
		cyclicComponent := pattern.Amplitude * math.Sin(freq*float64(futureIndex)+pattern.Phase)
		predicted += cyclicComponent * pattern.Confidence
		totalWeight += pattern.Confidence
	}

	confidence := 0.0
	if totalWeight > 0 {
		confidence = totalWeight / float64(len(patterns))
	}

	if predicted < 0 {
		predicted = 0
	}

	return predicted, confidence, nil
}

func (p *TimeSeriesPredictor) PredictWithCyclic(
	ts types.TimeSeriesData,
	predictionSteps int,
) (types.ResourcePrediction, error) {
	if !p.config.Enabled {
		return types.ResourcePrediction{}, nil
	}

	if !p.config.CyclicPredictionEnabled {
		return p.Predict(ts, predictionSteps)
	}

	patterns := p.DetectCyclicPatterns(ts)

	methods := []string{"exponential_smoothing", "arima", "holt_winters"}
	bestPrediction := 0.0
	bestConfidence := 0.0

	for _, method := range methods {
		prediction, confidence, err := p.predictWithMethod(ts, predictionSteps, method)
		if err != nil {
			p.logger.Debug("Prediction method %s failed: %v", method, err)
			continue
		}

		if confidence > bestConfidence {
			bestConfidence = confidence
			bestPrediction = prediction
		}
	}

	if len(patterns) > 0 {
		fourierPred, fourierConf, err := p.FourierPrediction(ts, predictionSteps, patterns)
		if err == nil {
			if fourierConf > bestConfidence {
				bestConfidence = fourierConf
				bestPrediction = fourierPred
			} else {
				bestPrediction = bestPrediction*0.7 + fourierPred*0.3
				bestConfidence = (bestConfidence + fourierConf) / 2
			}
		}

		p.logger.Debug("Detected %d cyclic patterns, strongest period=%d, confidence=%.3f",
			len(patterns), patterns[0].Period, patterns[0].Confidence)

		if p.config.PreAdjustmentLeadMinutes > 0 && len(patterns[0].PeakHours) > 0 {
			p.logger.Debug("Peak hours detected: %v, pre-adjustment lead: %d minutes",
				patterns[0].PeakHours, p.config.PreAdjustmentLeadMinutes)
		}
	}

	if bestConfidence == 0 {
		return types.ResourcePrediction{}, fmt.Errorf("all prediction methods failed")
	}

	return types.ResourcePrediction{
		CPUPredictedUsage:    bestPrediction,
		MemoryPredictedUsage: bestPrediction,
		ConfidenceInterval:   bestConfidence,
		PredictionWindow:     p.config.PredictionWindow,
	}, nil
}

func (p *TimeSeriesPredictor) GetPeakForecast(
	ts types.TimeSeriesData,
	hoursAhead int,
) (*CyclicPattern, float64) {
	patterns := p.DetectCyclicPatterns(ts)
	if len(patterns) == 0 {
		return nil, 0
	}

	bestPattern := patterns[0]
	for _, pat := range patterns {
		if pat.Confidence > bestPattern.Confidence {
			bestPattern = pat
		}
	}

	now := time.Now()
	targetTime := now.Add(time.Duration(hoursAhead) * time.Hour)
	hourOfDay := targetTime.Hour()

	stepsPerHour := 12
	if p.config.SeasonalPeriod > 0 {
		stepsPerHour = p.config.SeasonalPeriod / 24
	}
	if stepsPerHour == 0 {
		stepsPerHour = 1
	}

	targetStep := len(ts.Values) + hoursAhead*stepsPerHour
	freq := 2.0 * math.Pi / float64(bestPattern.Period)
	forecast := bestPattern.Amplitude * math.Sin(freq*float64(targetStep)+bestPattern.Phase)

	_ = hourOfDay

	return &bestPattern, forecast
}

func (p *TimeSeriesPredictor) PredictNext24Hours(
	ts types.TimeSeriesData,
	resourceType string,
) (*types.DayPrediction, error) {
	n := len(ts.Values)
	if n < 48 {
		return nil, fmt.Errorf("insufficient data for 24h prediction, need at least 48 points")
	}

	hourlySteps := 12
	if p.config.SeasonalPeriod > 0 {
		hourlySteps = p.config.SeasonalPeriod / 24
	}
	if hourlySteps == 0 {
		hourlySteps = 1
	}

	patterns := p.DetectCyclicPatterns(ts)
	dayPrediction := &types.DayPrediction{
		HourlyPredictions: make([]types.HourlyPrediction, 24),
	}

	totalCPU := 0.0
	totalMemory := 0.0
	peakCPU := 0.0
	peakMemory := 0.0
	peakHour := 0

	for hour := 0; hour < 24; hour++ {
		predictionSteps := (hour + 1) * hourlySteps
		confidence := 0.7

		var predValue float64

		if len(patterns) > 0 {
			fourierPred, fourierConf, err := p.FourierPrediction(ts, predictionSteps, patterns)
			if err == nil {
				predValue = fourierPred
				confidence = fourierConf
			}
		}

		if predValue == 0 {
			basePred, baseConf, err := p.exponentialSmoothing(ts, predictionSteps)
			if err == nil {
				predValue = basePred
				confidence = baseConf
			}
		}

		if predValue < 0 {
			predValue = 0
		}

		hourlyPred := types.HourlyPrediction{
			Hour:       hour,
			Confidence: confidence,
		}

		switch resourceType {
		case "cpu":
			hourlyPred.CPUPredicted = predValue
			hourlyPred.MemoryPredicted = 0
			totalCPU += predValue
			if predValue > peakCPU {
				peakCPU = predValue
				peakHour = hour
			}
		case "memory":
			hourlyPred.CPUPredicted = 0
			hourlyPred.MemoryPredicted = predValue
			totalMemory += predValue
			if predValue > peakMemory {
				peakMemory = predValue
				peakHour = hour
			}
		default:
			hourlyPred.CPUPredicted = predValue
			hourlyPred.MemoryPredicted = predValue
			totalCPU += predValue
			totalMemory += predValue
			if predValue > peakCPU {
				peakCPU = predValue
				peakHour = hour
			}
		}

		dayPrediction.HourlyPredictions[hour] = hourlyPred
	}

	dayPrediction.PeakHour = peakHour
	dayPrediction.PeakCPU = peakCPU
	dayPrediction.PeakMemory = peakMemory
	dayPrediction.AvgCPU = totalCPU / 24
	dayPrediction.AvgMemory = totalMemory / 24

	preAllocation := p.config.PeakPreAllocation
	if preAllocation == 0 {
		preAllocation = 0.2
	}

	switch resourceType {
	case "cpu":
		dayPrediction.RecommendedLimit = peakCPU * (1 + preAllocation)
	case "memory":
		dayPrediction.RecommendedLimit = peakMemory * (1 + preAllocation)
	default:
		dayPrediction.RecommendedLimit = peakCPU * (1 + preAllocation)
	}

	return dayPrediction, nil
}

func (p *TimeSeriesPredictor) GetPeakAdjustmentRecommendation(
	cpuPrediction *types.DayPrediction,
	memPrediction *types.DayPrediction,
	currentCPULimit float64,
	currentMemoryLimit float64,
	config config.ScalingConfig,
) (bool, float64, float64, string) {
	if cpuPrediction == nil && memPrediction == nil {
		return false, 0, 0, "no prediction data"
	}

	shouldAdjust := false
	recommendedCPULimit := currentCPULimit
	recommendedMemoryLimit := currentMemoryLimit
	reasons := make([]string, 0)

	if cpuPrediction != nil && cpuPrediction.RecommendedLimit > 0 {
		headroom := config.UtilizationHighThreshold
		expectedPeakUsagePct := cpuPrediction.PeakCPU / currentCPULimit

		if expectedPeakUsagePct > headroom {
			shouldAdjust = true
			recommendedCPULimit = cpuPrediction.RecommendedLimit
			if recommendedCPULimit > config.MaxCPULimit {
				recommendedCPULimit = config.MaxCPULimit
			}
			reasons = append(reasons, fmt.Sprintf(
				"CPU peak %.0fm at hour %d exceeds %.0f%% of limit %.0fm",
				cpuPrediction.PeakCPU, cpuPrediction.PeakHour,
				headroom*100, currentCPULimit,
			))
		}
	}

	if memPrediction != nil && memPrediction.RecommendedLimit > 0 {
		headroom := config.UtilizationHighThreshold
		expectedPeakUsagePct := memPrediction.PeakMemory / currentMemoryLimit

		if expectedPeakUsagePct > headroom {
			shouldAdjust = true
			recommendedMemoryLimit = memPrediction.RecommendedLimit
			if recommendedMemoryLimit > config.MaxMemoryLimit {
				recommendedMemoryLimit = config.MaxMemoryLimit
			}
			reasons = append(reasons, fmt.Sprintf(
				"Memory peak %.0fMi at hour %d exceeds %.0f%% of limit %.0fMi",
				memPrediction.PeakMemory, memPrediction.PeakHour,
				headroom*100, currentMemoryLimit,
			))
		}
	}

	if len(reasons) == 0 {
		return false, 0, 0, "no peak adjustment needed"
	}

	return shouldAdjust, recommendedCPULimit, recommendedMemoryLimit, strings.Join(reasons, "; ")
}

func (p *TimeSeriesPredictor) Predict(
	ts types.TimeSeriesData,
	predictionSteps int,
) (types.ResourcePrediction, error) {
	if !p.config.Enabled {
		return types.ResourcePrediction{}, nil
	}

	if len(ts.Values) < p.config.SeasonalPeriod*2 {
		p.logger.Warning("Insufficient data for prediction, need at least %d points",
			p.config.SeasonalPeriod*2)
		return types.ResourcePrediction{}, fmt.Errorf("insufficient data")
	}

	methods := []string{"exponential_smoothing", "arima", "holt_winters"}
	bestPrediction := 0.0
	bestConfidence := 0.0

	for _, method := range methods {
		prediction, confidence, err := p.predictWithMethod(ts, predictionSteps, method)
		if err != nil {
			p.logger.Debug("Prediction method %s failed: %v", method, err)
			continue
		}

		if confidence > bestConfidence {
			bestConfidence = confidence
			bestPrediction = prediction
		}
	}

	if bestConfidence == 0 {
		return types.ResourcePrediction{}, fmt.Errorf("all prediction methods failed")
	}

	return types.ResourcePrediction{
		CPUPredictedUsage:    bestPrediction,
		MemoryPredictedUsage: bestPrediction,
		ConfidenceInterval:   bestConfidence,
		PredictionWindow:     p.config.PredictionWindow,
	}, nil
}

func (p *TimeSeriesPredictor) predictWithMethod(
	ts types.TimeSeriesData,
	predictionSteps int,
	method string,
) (float64, float64, error) {
	switch method {
	case "exponential_smoothing":
		return p.exponentialSmoothing(ts, predictionSteps)
	case "arima":
		return p.arima(ts, predictionSteps)
	case "holt_winters":
		return p.holtWinters(ts, predictionSteps)
	default:
		return 0, 0, fmt.Errorf("unknown method: %s", method)
	}
}

func (p *TimeSeriesPredictor) exponentialSmoothing(
	ts types.TimeSeriesData,
	predictionSteps int,
) (float64, float64, error) {
	n := len(ts.Values)
	trainingSize := int(float64(n) * p.config.TrainingDataRatio)
	training := ts.Values[:trainingSize]

	alpha := 0.3
	beta := 0.1

	level := training[0]
	trend := 0.0
	if len(training) > 1 {
		trend = (training[1] - training[0])
	}

	for i := 1; i < len(training); i++ {
		prevLevel := level
		level = alpha*training[i] + (1-alpha)*(level+trend)
		trend = beta*(level-prevLevel) + (1-beta)*trend
	}

	predicted := make([]float64, predictionSteps)
	for i := 0; i < predictionSteps; i++ {
		predicted[i] = level + float64(i+1)*trend
	}

	actual := ts.Values[trainingSize:]
	if len(actual) > 0 {
		minLen := len(predicted)
		if len(actual) < minLen {
			minLen = len(actual)
		}
		confidence := calculateConfidence(actual[:minLen], predicted[:minLen])
		return predicted[predictionSteps-1], confidence, nil
	}

	return predicted[predictionSteps-1], 0.5, nil
}

func (p *TimeSeriesPredictor) arima(
	ts types.TimeSeriesData,
	predictionSteps int,
) (float64, float64, error) {
	n := len(ts.Values)
	trainingSize := int(float64(n) * p.config.TrainingDataRatio)
	training := ts.Values[:trainingSize]

	order := p.config.ARIMAOrder
	if len(order) < 3 {
		order = []int{1, 1, 1}
	}

	p, d, q := order[0], order[1], order[2]

	differenced := make([]float64, 0)
	current := training
	for i := 0; i < d; i++ {
		if len(current) < 2 {
			break
		}
		diff := make([]float64, len(current)-1)
		for j := 0; j < len(diff); j++ {
			diff[j] = current[j+1] - current[j]
		}
		differenced = diff
		current = diff
	}

	if len(differenced) < p+q {
		return 0, 0, fmt.Errorf("insufficient data after differencing")
	}

	arCoeffs := fitAR(differenced, p)
	maCoeffs := fitMA(differenced, q)

	predicted := make([]float64, predictionSteps)
	history := make([]float64, p)
	copy(history, differenced[len(differenced)-p:])

	residuals := make([]float64, q)

	for step := 0; step < predictionSteps; step++ {
		arPart := 0.0
		for i := 0; i < p; i++ {
			if i < len(arCoeffs) && i < len(history) {
				arPart += arCoeffs[i] * history[p-1-i]
			}
		}

		maPart := 0.0
		for i := 0; i < q; i++ {
			if i < len(maCoeffs) && i < len(residuals) {
				maPart += maCoeffs[i] * residuals[q-1-i]
			}
		}

		predDiff := arPart + maPart
		predicted[step] = predDiff

		for i := 0; i < p-1; i++ {
			history[i] = history[i+1]
		}
		if p > 0 {
			history[p-1] = predDiff
		}
	}

	integrated := integrateSeries(predicted, training, d)

	actual := ts.Values[trainingSize:]
	confidence := 0.5
	if len(actual) > 0 {
		minLen := len(integrated)
		if len(actual) < minLen {
			minLen = len(actual)
		}
		confidence = calculateConfidence(actual[:minLen], integrated[:minLen])
	}

	return integrated[predictionSteps-1], confidence, nil
}

func (p *TimeSeriesPredictor) holtWinters(
	ts types.TimeSeriesData,
	predictionSteps int,
) (float64, float64, error) {
	n := len(ts.Values)
	seasonalPeriod := p.config.SeasonalPeriod

	if n < seasonalPeriod*2 {
		return 0, 0, fmt.Errorf("insufficient data for seasonal decomposition")
	}

	trainingSize := int(float64(n) * p.config.TrainingDataRatio)
	training := ts.Values[:trainingSize]

	alpha := 0.3
	beta := 0.1
	gamma := 0.2

	level := 0.0
	for i := 0; i < seasonalPeriod; i++ {
		level += training[i]
	}
	level /= float64(seasonalPeriod)

	trend := 0.0
	if len(training) > seasonalPeriod {
		level2 := 0.0
		for i := seasonalPeriod; i < seasonalPeriod*2 && i < len(training); i++ {
			level2 += training[i]
		}
		count := float64(len(training) - seasonalPeriod)
		if count > 0 {
			level2 /= count
			trend = (level2 - level) / float64(seasonalPeriod)
		}
	}

	seasonal := make([]float64, seasonalPeriod)
	for i := 0; i < seasonalPeriod && i < len(training); i++ {
		seasonal[i] = training[i] - level
	}

	for i := seasonalPeriod; i < len(training); i++ {
		prevLevel := level
		seasonIdx := i % seasonalPeriod

		level = alpha*(training[i]-seasonal[seasonIdx]) + (1-alpha)*(level+trend)
		trend = beta*(level-prevLevel) + (1-beta)*trend
		seasonal[seasonIdx] = gamma*(training[i]-level) + (1-gamma)*seasonal[seasonIdx]
	}

	predicted := make([]float64, predictionSteps)
	for i := 0; i < predictionSteps; i++ {
		seasonIdx := (len(training) + i) % seasonalPeriod
		predicted[i] = level + float64(i+1)*trend + seasonal[seasonIdx]
	}

	actual := ts.Values[trainingSize:]
	confidence := 0.5
	if len(actual) > 0 {
		minLen := len(predicted)
		if len(actual) < minLen {
			minLen = len(actual)
		}
		confidence = calculateConfidence(actual[:minLen], predicted[:minLen])
	}

	return predicted[predictionSteps-1], confidence, nil
}

func fitAR(data []float64, p int) []float64 {
	if len(data) <= p {
		return make([]float64, p)
	}

	x := make([][]float64, len(data)-p)
	y := make([]float64, len(data)-p)

	for i := p; i < len(data); i++ {
		x[i-p] = make([]float64, p)
		for j := 0; j < p; j++ {
			x[i-p][j] = data[i-1-j]
		}
		y[i-p] = data[i]
	}

	coefficients := make([]float64, p)
	if len(x) == 0 || len(x[0]) == 0 {
		return coefficients
	}

	a := make([][]float64, p)
	for i := range a {
		a[i] = make([]float64, p)
	}

	b := make([]float64, p)

	for i := 0; i < p; i++ {
		for j := 0; j < p; j++ {
			sum := 0.0
			for k := 0; k < len(x); k++ {
				sum += x[k][i] * x[k][j]
			}
			a[i][j] = sum
		}

		sum := 0.0
		for k := 0; k < len(x); k++ {
			sum += x[k][i] * y[k]
		}
		b[i] = sum
	}

	result := gaussianElimination(a, b)
	if result != nil {
		return result
	}

	return coefficients
}

func fitMA(data []float64, q int) []float64 {
	coefficients := make([]float64, q)
	if len(data) <= q {
		return coefficients
	}

	residuals := make([]float64, len(data))
	mean := 0.0
	for _, v := range data {
		mean += v
	}
	mean /= float64(len(data))

	for i, v := range data {
		residuals[i] = v - mean
	}

	for i := 0; i < q && i < len(residuals)-1; i++ {
		coefficients[i] = 0.1
	}

	return coefficients
}

func integrateSeries(differenced []float64, original []float64, d int) []float64 {
	result := make([]float64, len(differenced))
	copy(result, differenced)

	for i := 0; i < d; i++ {
		integrated := make([]float64, len(result))
		lastValue := original[len(original)-1]
		for j := 0; j < len(result); j++ {
			if j == 0 {
				integrated[j] = lastValue + result[j]
			} else {
				integrated[j] = integrated[j-1] + result[j]
			}
		}
		result = integrated
	}

	return result
}

func calculateConfidence(actual, predicted []float64) float64 {
	n := len(actual)
	if n == 0 {
		return 0.5
	}

	mape := 0.0
	count := 0
	for i := 0; i < n; i++ {
		if actual[i] != 0 {
			mape += math.Abs((actual[i] - predicted[i]) / actual[i])
			count++
		}
	}

	if count == 0 {
		return 0.5
	}

	mape /= float64(count)
	confidence := 1 - mape

	if confidence < 0 {
		confidence = 0
	}
	if confidence > 1 {
		confidence = 1
	}

	return confidence
}

func gaussianElimination(a [][]float64, b []float64) []float64 {
	n := len(a)
	if n == 0 {
		return nil
	}

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
			continue
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
		if math.Abs(augmented[i][i]) > 1e-10 {
			result[i] = sum / augmented[i][i]
		}
	}

	return result
}
