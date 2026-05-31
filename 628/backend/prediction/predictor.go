package prediction

import (
	"fmt"
	"math"
	"sort"
	"time"

	"anomaly-detector/detector"
	"anomaly-detector/model"
)

type Predictor struct {
	horizon       time.Duration
	warningThreshold float64
	period        int
}

func NewPredictor(horizon time.Duration, warningThreshold float64, period int) *Predictor {
	if horizon <= 0 {
		horizon = 30 * time.Minute
	}
	if warningThreshold <= 0 {
		warningThreshold = 0.7
	}
	if period <= 0 {
		period = 60
	}
	return &Predictor{
		horizon:          horizon,
		warningThreshold: warningThreshold,
		period:           period,
	}
}

func (p *Predictor) Predict(ts model.TimeSeries) []model.Prediction {
	if len(ts.Points) < 20 {
		return nil
	}

	data := make([]float64, len(ts.Points))
	for i, pt := range ts.Points {
		data[i] = pt.Value
	}

	var predictions []model.Prediction

	if pred := p.predictByTrend(ts.Name, data, ts.Points); pred != nil {
		predictions = append(predictions, *pred)
	}

	if pred := p.predictBySeasonal(ts.Name, data, ts.Points); pred != nil {
		predictions = append(predictions, *pred)
	}

	if pred := p.predictByRateOfChange(ts.Name, data, ts.Points); pred != nil {
		predictions = append(predictions, *pred)
	}

	if pred := p.predictByVolatility(ts.Name, data, ts.Points); pred != nil {
		predictions = append(predictions, *pred)
	}

	predictions = p.deduplicate(predictions)

	sort.Slice(predictions, func(i, j int) bool {
		return predictions[i].Confidence > predictions[j].Confidence
	})

	return predictions
}

func (p *Predictor) PredictBatch(series []model.TimeSeries) model.PredictionResult {
	var allPredictions []model.Prediction

	for _, ts := range series {
		predictions := p.Predict(ts)
		allPredictions = append(allPredictions, predictions...)
	}

	filtered := make([]model.Prediction, 0)
	for _, pred := range allPredictions {
		if pred.Confidence >= p.warningThreshold {
			filtered = append(filtered, pred)
		}
	}

	return model.PredictionResult{
		Predictions:  filtered,
		AnalysisTime: time.Now(),
		Horizon:      p.horizon,
	}
}

func (p *Predictor) predictByTrend(name string, data []float64, points []model.TimeSeriesPoint) *model.Prediction {
	n := len(data)
	windowSize := minInt(n/3, 30)
	if windowSize < 5 {
		return nil
	}

	recent := data[n-windowSize:]

	slope, intercept := linearRegression(recent)

	slopeAbs := math.Abs(slope)
	recentMean := 0.0
	for _, v := range recent {
		recentMean += v
	}
	recentMean /= float64(len(recent))

	if recentMean == 0 {
		return nil
	}
	relativeSlope := slopeAbs / math.Abs(recentMean)

	if relativeSlope < 0.01 {
		return nil
	}

	stlResult := detector.STLDecompose(data, p.period, 3)
	residualStd := stdDev(stlResult.Remainder)

	lastTrend := stlResult.Trend[n-1]

	stepsAhead := int(p.horizon.Minutes())
	if stepsAhead < 1 {
		stepsAhead = 30
	}

	predictedValue := lastTrend + slope*float64(stepsAhead)
	upperBound := predictedValue + 2*residualStd
	lowerBound := predictedValue - 2*residualStd

	seasonalRange := 0.0
	if len(stlResult.Seasonal) > 0 {
		seasonalMax := maxSlice(stlResult.Seasonal)
		seasonalMin := minSlice(stlResult.Seasonal)
		seasonalRange = seasonalMax - seasonalMin
	}

	normalUpper := recentMean + 2*residualStd + seasonalRange/2
	normalLower := recentMean - 2*residualStd - seasonalRange/2

	direction := model.DirectionBoth
	willExceed := false
	threshold := 0.0

	if predictedValue > normalUpper {
		direction = model.DirectionUp
		threshold = normalUpper
		willExceed = true
	} else if predictedValue < normalLower {
		direction = model.DirectionDown
		threshold = normalLower
		willExceed = true
	}

	if !willExceed {
		if predictedValue > upperBound && relativeSlope > 0.05 {
			direction = model.DirectionUp
			threshold = upperBound
			willExceed = true
		} else if predictedValue < lowerBound && relativeSlope > 0.05 {
			direction = model.DirectionDown
			threshold = lowerBound
			willExceed = true
		}
	}

	if !willExceed {
		return nil
	}

	distanceFromNormal := 0.0
	if direction == model.DirectionUp {
		distanceFromNormal = (predictedValue - normalUpper) / (residualStd + 1)
	} else {
		distanceFromNormal = (normalLower - predictedValue) / (residualStd + 1)
	}

	confidence := math.Min(0.3+relativeSlope*3+distanceFromNormal*0.1, 0.95)
	if confidence < p.warningThreshold {
		return nil
	}

	predictedTime := points[n-1].Timestamp.Add(p.horizon)

	var reason string
	if direction == model.DirectionUp {
		reason = fmt.Sprintf("趋势上升: 当前值%.2f以斜率%.4f增长，预计%d分钟后超过正常上界%.2f",
			data[n-1], slope, stepsAhead, normalUpper)
	} else {
		reason = fmt.Sprintf("趋势下降: 当前值%.2f以斜率%.4f降低，预计%d分钟后低于正常下界%.2f",
			data[n-1], slope, stepsAhead, normalLower)
	}

	return &model.Prediction{
		Metric:        name,
		PredictedTime: predictedTime,
		Direction:     direction,
		Confidence:    confidence,
		CurrentValue:  data[n-1],
		Threshold:     threshold,
		TrendSlope:    slope,
		Reason:        reason,
	}
}

func (p *Predictor) predictBySeasonal(name string, data []float64, points []model.TimeSeriesPoint) *model.Prediction {
	n := len(data)
	if n < 2*p.period {
		return nil
	}

	stlResult := detector.STLDecompose(data, p.period, 3)

	lastCycleSeasonal := stlResult.Seasonal[n-p.period:]

	peakIdx := 0
	peakVal := 0.0
	for i, v := range lastCycleSeasonal {
		if math.Abs(v) > math.Abs(peakVal) {
			peakVal = v
			peakIdx = i
		}
	}

	residualStd := stdDev(stlResult.Remainder)
	thresholdVal := 2 * residualStd

	if math.Abs(peakVal) < thresholdVal {
		return nil
	}

	stepsToPeak := peakIdx + 1
	if stepsToPeak <= 0 {
		return nil
	}

	peakTime := points[n-1].Timestamp.Add(time.Duration(stepsToPeak) * time.Minute)

	if peakTime.After(points[n-1].Timestamp.Add(p.horizon)) {
		return nil
	}

	predictedValue := stlResult.Trend[n-1] + peakVal
	currentValue := data[n-1]

	direction := model.DirectionBoth
	if peakVal > 0 {
		direction = model.DirectionUp
	} else {
		direction = model.DirectionDown
	}

	confidence := math.Min(math.Abs(peakVal)/(thresholdVal+1)*0.4+0.3, 0.9)

	seasonalConsistency := p.checkSeasonalConsistency(stlResult.Seasonal)
	confidence *= seasonalConsistency

	if confidence < p.warningThreshold {
		return nil
	}

	reason := fmt.Sprintf("周期性预测: 根据季节模式，%d分钟后预计出现%s峰值(季节分量%.2f)",
		stepsToPeak, directionLabel(direction), peakVal)

	return &model.Prediction{
		Metric:        name,
		PredictedTime: peakTime,
		Direction:     direction,
		Confidence:    confidence,
		CurrentValue:  currentValue,
		Threshold:     predictedValue - 2*residualStd,
		TrendSlope:    peakVal / float64(stepsToPeak),
		Reason:        reason,
	}
}

func (p *Predictor) predictByRateOfChange(name string, data []float64, points []model.TimeSeriesPoint) *model.Prediction {
	n := len(data)
	if n < 10 {
		return nil
	}

	windowSize := minInt(n/4, 20)
	if windowSize < 5 {
		return nil
	}

	rates := make([]float64, windowSize)
	for i := 0; i < windowSize; i++ {
		idx := n - windowSize + i
		if idx < 1 {
			continue
		}
		if data[idx-1] == 0 {
			rates[i] = 0
		} else {
			rates[i] = (data[idx] - data[idx-1]) / math.Abs(data[idx-1])
		}
	}

	acceleration := 0.0
	if len(rates) >= 4 {
		halfRates := rates[len(rates)/2:]
		firstHalfMean := sliceMean(rates[:len(rates)/2])
		secondHalfMean := sliceMean(halfRates)
		acceleration = secondHalfMean - firstHalfMean
	}

	currentRate := rates[len(rates)-1]

	if math.Abs(currentRate) < 0.02 && math.Abs(acceleration) < 0.01 {
		return nil
	}

	stlResult := detector.STLDecompose(data, p.period, 3)
	residualStd := stdDev(stlResult.Remainder)
	recentMean := sliceMean(data[n-windowSize:])

	var predictedValue float64
	stepsAhead := 10

	if math.Abs(acceleration) > 0.005 {
		predictedValue = data[n-1] * (1 + currentRate*float64(stepsAhead) + 0.5*acceleration*float64(stepsAhead*stepsAhead))
	} else {
		predictedValue = data[n-1] * (1 + currentRate*float64(stepsAhead))
	}

	upperBound := recentMean + 3*residualStd
	lowerBound := recentMean - 3*residualStd

	direction := model.DirectionBoth
	willExceed := false
	threshold := 0.0

	if predictedValue > upperBound {
		direction = model.DirectionUp
		threshold = upperBound
		willExceed = true
	} else if predictedValue < lowerBound {
		direction = model.DirectionDown
		threshold = lowerBound
		willExceed = true
	}

	if !willExceed {
		return nil
	}

	confidence := math.Min(math.Abs(currentRate)*10+math.Abs(acceleration)*50+0.3, 0.9)
	if confidence < p.warningThreshold {
		return nil
	}

	predictedTime := points[n-1].Timestamp.Add(time.Duration(stepsAhead) * time.Minute)

	reason := fmt.Sprintf("变化率异常: 当前变化率%.2f%%/步，加速度%.4f，预计持续%s导致%s",
		currentRate*100, acceleration, directionLabel(direction), directionLabel(direction))

	return &model.Prediction{
		Metric:        name,
		PredictedTime: predictedTime,
		Direction:     direction,
		Confidence:    confidence,
		CurrentValue:  data[n-1],
		Threshold:     threshold,
		TrendSlope:    currentRate,
		Reason:        reason,
	}
}

func (p *Predictor) predictByVolatility(name string, data []float64, points []model.TimeSeriesPoint) *model.Prediction {
	n := len(data)
	if n < 20 {
		return nil
	}

	windowSize := minInt(n/3, 30)

	recentStd := stdDev(data[n-windowSize:])
	overallStd := stdDev(data)

	if overallStd == 0 {
		return nil
	}

	volatilityRatio := recentStd / overallStd

	if volatilityRatio < 1.5 {
		return nil
	}

	stlResult := detector.STLDecompose(data, p.period, 3)
	residual := stlResult.Remainder

	extremeCount := 0
	threshold := 2 * overallStd
	for i := len(residual) - windowSize; i < len(residual); i++ {
		if i < 0 {
			continue
		}
		if math.Abs(residual[i]) > threshold {
			extremeCount++
		}
	}

	if extremeCount < 2 {
		return nil
	}

	confidence := math.Min(0.3+volatilityRatio*0.15+float64(extremeCount)*0.05, 0.85)
	if confidence < p.warningThreshold {
		return nil
	}

	predictedTime := points[n-1].Timestamp.Add(5 * time.Minute)

	direction := model.DirectionBoth
	if data[n-1] > data[n-2] {
		direction = model.DirectionUp
	} else {
		direction = model.DirectionDown
	}

	recentMean := sliceMean(data[n-windowSize:])

	reason := fmt.Sprintf("波动率异常: 近期波动率是整体的%.1f倍，出现%d次极端残差，可能即将发生异常",
		volatilityRatio, extremeCount)

	return &model.Prediction{
		Metric:        name,
		PredictedTime: predictedTime,
		Direction:     direction,
		Confidence:    confidence,
		CurrentValue:  data[n-1],
		Threshold:     recentMean + 2*recentStd,
		TrendSlope:    volatilityRatio,
		Reason:        reason,
	}
}

func (p *Predictor) checkSeasonalConsistency(seasonal []float64) float64 {
	if len(seasonal) < 2*p.period {
		return 0.5
	}

	firstCycle := seasonal[:p.period]
	secondCycle := seasonal[p.period : 2*p.period]

	if len(firstCycle) == 0 || len(secondCycle) == 0 {
		return 0.5
	}

	minLen := minInt(len(firstCycle), len(secondCycle))
	if minLen < 3 {
		return 0.5
	}

	corr := simpleCorrelation(firstCycle[:minLen], secondCycle[:minLen])

	return 0.5 + 0.5*math.Max(corr, 0)
}

func (p *Predictor) deduplicate(predictions []model.Prediction) []model.Prediction {
	best := make(map[string]model.Prediction)
	for _, pred := range predictions {
		key := pred.Metric + "-" + string(pred.Direction)
		if existing, ok := best[key]; !ok || pred.Confidence > existing.Confidence {
			best[key] = pred
		}
	}

	result := make([]model.Prediction, 0, len(best))
	for _, pred := range best {
		result = append(result, pred)
	}
	return result
}

func linearRegression(data []float64) (slope, intercept float64) {
	n := float64(len(data))
	if n < 2 {
		return 0, 0
	}

	sumX := 0.0
	sumY := 0.0
	sumXY := 0.0
	sumX2 := 0.0

	for i, y := range data {
		x := float64(i)
		sumX += x
		sumY += y
		sumXY += x * y
		sumX2 += x * x
	}

	denom := n*sumX2 - sumX*sumX
	if denom == 0 {
		return 0, sumY / n
	}

	slope = (n*sumXY - sumX*sumY) / denom
	intercept = (sumY - slope*sumX) / n

	return slope, intercept
}

func stdDev(data []float64) float64 {
	if len(data) < 2 {
		return 0
	}
	m := sliceMean(data)
	sum := 0.0
	for _, v := range data {
		d := v - m
		sum += d * d
	}
	return math.Sqrt(sum / float64(len(data)-1))
}

func sliceMean(data []float64) float64 {
	if len(data) == 0 {
		return 0
	}
	sum := 0.0
	for _, v := range data {
		sum += v
	}
	return sum / float64(len(data))
}

func maxSlice(data []float64) float64 {
	if len(data) == 0 {
		return 0
	}
	m := data[0]
	for _, v := range data[1:] {
		if v > m {
			m = v
		}
	}
	return m
}

func minSlice(data []float64) float64 {
	if len(data) == 0 {
		return 0
	}
	m := data[0]
	for _, v := range data[1:] {
		if v < m {
			m = v
		}
	}
	return m
}

func simpleCorrelation(x, y []float64) float64 {
	n := len(x)
	if n != len(y) || n < 3 {
		return 0
	}

	meanX := sliceMean(x)
	meanY := sliceMean(y)

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

func directionLabel(d model.AnomalyDirection) string {
	switch d {
	case model.DirectionUp:
		return "上升"
	case model.DirectionDown:
		return "下降"
	default:
		return "变化"
	}
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}
