package predictor

import (
	"math"
	"time"

	"github.com/montanaflynn/stats"
	"github.com/sirupsen/logrus"
)

type LagDataPoint struct {
	Timestamp time.Time
	Lag       int64
}

type Prediction struct {
	PredictedLag     int64
	PredictionTime   time.Time
	Confidence       float64
	Trend            string
	RateOfChange     float64
	Method           string
	ProcessingRate   float64
	ArrivalRate      float64
	ProcessTimePerMsg time.Duration
}

type Predictor struct {
	logger *logrus.Logger
}

func NewPredictor(logger *logrus.Logger) *Predictor {
	return &Predictor{
		logger: logger,
	}
}

func (p *Predictor) PredictLinearRegression(data []LagDataPoint, predictionWindow time.Duration) *Prediction {
	if len(data) < 2 {
		return nil
	}

	x := make([]float64, len(data))
	y := make([]float64, len(data))

	firstTime := data[0].Timestamp
	for i, point := range data {
		x[i] = point.Timestamp.Sub(firstTime).Seconds()
		y[i] = float64(point.Lag)
	}

	slope, intercept, r, err := linearRegression(x, y)
	if err != nil {
		p.logger.Warnf("Linear regression failed: %v", err)
		return nil
	}

	predictionTime := time.Now().Add(predictionWindow)
	predictionX := predictionTime.Sub(firstTime).Seconds()
	predictedY := slope*predictionX + intercept

	trend := "stable"
	if slope > 0.1 {
		trend = "increasing"
	} else if slope < -0.1 {
		trend = "decreasing"
	}

	if predictedY < 0 {
		predictedY = 0
	}

	confidence := math.Abs(r)

	return &Prediction{
		PredictedLag:   int64(math.Round(predictedY)),
		PredictionTime: predictionTime,
		Confidence:     confidence,
		Trend:          trend,
		RateOfChange:   slope,
		Method:         "linear_regression",
	}
}

func linearRegression(x, y []float64) (slope, intercept, r float64, err error) {
	if len(x) != len(y) || len(x) == 0 {
		return 0, 0, 0, nil
	}

	var sumX, sumY, sumXY, sumX2, sumY2 float64
	n := float64(len(x))

	for i := 0; i < len(x); i++ {
		sumX += x[i]
		sumY += y[i]
		sumXY += x[i] * y[i]
		sumX2 += x[i] * x[i]
		sumY2 += y[i] * y[i]
	}

	denominator := n*sumX2 - sumX*sumX
	if denominator == 0 {
		return 0, sumY / n, 0, nil
	}

	slope = (n*sumXY - sumX*sumY) / denominator
	intercept = (sumY - slope*sumX) / n

	rNumerator := n*sumXY - sumX*sumY
	rDenominator := math.Sqrt((n*sumX2 - sumX*sumX) * (n*sumY2 - sumY*sumY))
	if rDenominator != 0 {
		r = rNumerator / rDenominator
	}

	return slope, intercept, r, nil
}

func (p *Predictor) PredictExponentialSmoothing(data []LagDataPoint, predictionWindow time.Duration, alpha float64) *Prediction {
	if len(data) < 2 {
		return nil
	}

	if alpha <= 0 || alpha >= 1 {
		alpha = 0.3
	}

	smoothed := make([]float64, len(data))
	smoothed[0] = float64(data[0].Lag)

	for i := 1; i < len(data); i++ {
		smoothed[i] = alpha*float64(data[i].Lag) + (1-alpha)*smoothed[i-1]
	}

	currentValue := smoothed[len(smoothed)-1]
	previousValue := smoothed[len(smoothed)-2]

	timeInterval := data[len(data)-1].Timestamp.Sub(data[len(data)-2].Timestamp).Seconds()
	if timeInterval <= 0 {
		timeInterval = 1
	}

	trend := (currentValue - previousValue) / timeInterval

	predictionSteps := predictionWindow.Seconds() / timeInterval
	if predictionSteps < 1 {
		predictionSteps = 1
	}

	predictedLag := currentValue + trend*predictionSteps

	trendStr := "stable"
	if trend > 0.1 {
		trendStr = "increasing"
	} else if trend < -0.1 {
		trendStr = "decreasing"
	}

	if predictedLag < 0 {
		predictedLag = 0
	}

	return &Prediction{
		PredictedLag:   int64(math.Round(predictedLag)),
		PredictionTime: time.Now().Add(predictionWindow),
		Confidence:     alpha,
		Trend:          trendStr,
		RateOfChange:   trend,
		Method:         "exponential_smoothing",
	}
}

func (p *Predictor) PredictMovingAverage(data []LagDataPoint, predictionWindow time.Duration, windowSize int) *Prediction {
	if len(data) < windowSize {
		windowSize = len(data)
	}

	if windowSize == 0 {
		return nil
	}

	recentData := data[len(data)-windowSize:]
	var sum int64
	for _, point := range recentData {
		sum += point.Lag
	}
	average := float64(sum) / float64(windowSize)

	if len(data) >= 2 {
		olderData := data[:len(data)-windowSize]
		if len(olderData) >= windowSize {
			olderWindow := olderData[len(olderData)-windowSize:]
			var olderSum int64
			for _, point := range olderWindow {
				olderSum += point.Lag
			}
			olderAverage := float64(olderSum) / float64(windowSize)

			timeDiff := recentData[len(recentData)-1].Timestamp.Sub(olderWindow[0].Timestamp).Seconds()
			if timeDiff > 0 {
				rateOfChange := (average - olderAverage) / timeDiff

				trendStr := "stable"
				if rateOfChange > 0.1 {
					trendStr = "increasing"
				} else if rateOfChange < -0.1 {
					trendStr = "decreasing"
				}

				predictedLag := average + rateOfChange*predictionWindow.Seconds()
				if predictedLag < 0 {
					predictedLag = 0
				}

				return &Prediction{
					PredictedLag:   int64(math.Round(predictedLag)),
					PredictionTime: time.Now().Add(predictionWindow),
					Confidence:     0.7,
					Trend:          trendStr,
					RateOfChange:   rateOfChange,
					Method:         "moving_average",
				}
			}
		}
	}

	return &Prediction{
		PredictedLag:   int64(math.Round(average)),
		PredictionTime: time.Now().Add(predictionWindow),
		Confidence:     0.5,
		Trend:          "stable",
		RateOfChange:   0,
		Method:         "moving_average",
	}
}

func (p *Predictor) PredictEnsemble(data []LagDataPoint, predictionWindow time.Duration) *Prediction {
	predictions := []*Prediction{}

	if linPred := p.PredictLinearRegression(data, predictionWindow); linPred != nil {
		predictions = append(predictions, linPred)
	}

	if expPred := p.PredictExponentialSmoothing(data, predictionWindow, 0.3); expPred != nil {
		predictions = append(predictions, expPred)
	}

	if maPred := p.PredictMovingAverage(data, predictionWindow, 10); maPred != nil {
		predictions = append(predictions, maPred)
	}

	if len(predictions) == 0 {
		return nil
	}

	var weightedSum float64
	var totalWeight float64
	trendVotes := make(map[string]float64)
	var rateOfChangeSum float64

	for _, pred := range predictions {
		weight := pred.Confidence
		weightedSum += float64(pred.PredictedLag) * weight
		totalWeight += weight
		trendVotes[pred.Trend] += weight
		rateOfChangeSum += pred.RateOfChange * weight
	}

	if totalWeight == 0 {
		return nil
	}

	ensemblePrediction := weightedSum / totalWeight
	ensembleRateOfChange := rateOfChangeSum / totalWeight

	dominantTrend := "stable"
	maxVote := 0.0
	for trend, vote := range trendVotes {
		if vote > maxVote {
			maxVote = vote
			dominantTrend = trend
		}
	}

	if ensemblePrediction < 0 {
		ensemblePrediction = 0
	}

	return &Prediction{
		PredictedLag:   int64(math.Round(ensemblePrediction)),
		PredictionTime: time.Now().Add(predictionWindow),
		Confidence:     totalWeight / float64(len(predictions)),
		Trend:          dominantTrend,
		RateOfChange:   ensembleRateOfChange,
		Method:         "ensemble",
	}
}

func (p *Predictor) CalculateStatistics(data []LagDataPoint) map[string]float64 {
	if len(data) == 0 {
		return nil
	}

	values := make([]float64, len(data))
	for i, point := range data {
		values[i] = float64(point.Lag)
	}

	mean, _ := stats.Mean(values)
	median, _ := stats.Median(values)
	stddev, _ := stats.StandardDeviation(values)
	variance, _ := stats.Variance(values)
	min, _ := stats.Min(values)
	max, _ := stats.Max(values)
	percentile90, _ := stats.Percentile(values, 90)
	percentile95, _ := stats.Percentile(values, 95)

	return map[string]float64{
		"mean":        mean,
		"median":      median,
		"stddev":      stddev,
		"variance":    variance,
		"min":         min,
		"max":         max,
		"percentile90": percentile90,
		"percentile95": percentile95,
		"count":       float64(len(data)),
	}
}

func (p *Predictor) DetectAnomalies(data []LagDataPoint, thresholdMultiplier float64) []LagDataPoint {
	if len(data) < 3 {
		return nil
	}

	values := make([]float64, len(data))
	for i, point := range data {
		values[i] = float64(point.Lag)
	}

	mean, _ := stats.Mean(values)
	stddev, _ := stats.StandardDeviation(values)

	if stddev == 0 {
		return nil
	}

	upperThreshold := mean + thresholdMultiplier*stddev
	lowerThreshold := mean - thresholdMultiplier*stddev

	var anomalies []LagDataPoint
	for i, point := range data {
		if values[i] > upperThreshold || values[i] < lowerThreshold {
			anomalies = append(anomalies, point)
		}
	}

	return anomalies
}

func (p *Predictor) ForecastRecoveryTime(data []LagDataPoint, targetLag int64) (time.Duration, bool) {
	if len(data) < 2 {
		return 0, false
	}

	linearPred := p.PredictLinearRegression(data, time.Hour)
	if linearPred == nil {
		return 0, false
	}

	if linearPred.RateOfChange >= 0 {
		return 0, false
	}

	currentLag := data[len(data)-1].Lag
	if currentLag <= targetLag {
		return 0, true
	}

	lagToReduce := float64(currentLag - targetLag)
	timeToRecover := lagToReduce / math.Abs(linearPred.RateOfChange)

	return time.Duration(timeToRecover * float64(time.Second)), true
}

func (p *Predictor) CalculateGrowthRate(data []LagDataPoint, windowSize int) (float64, bool) {
	if len(data) < windowSize+1 {
		windowSize = len(data) - 1
	}

	if windowSize < 1 {
		return 0, false
	}

	recentIndex := len(data) - 1
	oldIndex := len(data) - 1 - windowSize

	recentLag := float64(data[recentIndex].Lag)
	oldLag := float64(data[oldIndex].Lag)

	timeDiff := data[recentIndex].Timestamp.Sub(data[oldIndex].Timestamp).Seconds()
	if timeDiff <= 0 {
		return 0, false
	}

	growthRate := (recentLag - oldLag) / oldLag
	return growthRate, true
}

func (p *Predictor) PredictRequiredReplicas(
	currentReplicas int32,
	currentLag int64,
	targetLag int64,
	historicalEfficiency float64,
) int32 {
	if historicalEfficiency <= 0 {
		historicalEfficiency = 1.0
	}

	if currentLag <= targetLag {
		return currentReplicas
	}

	lagRatio := float64(currentLag) / float64(targetLag)
	requiredReplicas := float64(currentReplicas) * lagRatio / historicalEfficiency

	requiredReplicas = math.Ceil(requiredReplicas)

	return int32(requiredReplicas)
}

func (p *Predictor) CalculateOptimalReplicas(
	currentReplicas int32,
	currentLag int64,
	predictedLag5m int64,
	predictedLag15m int64,
	targetLag int64,
	maxReplicas int32,
	minReplicas int32,
) int32 {
	weightedLag := float64(currentLag)*0.2 + float64(predictedLag5m)*0.3 + float64(predictedLag15m)*0.5

	if weightedLag <= float64(targetLag) {
		if currentReplicas > minReplicas {
			reductionRatio := float64(targetLag) / weightedLag
			optimalReplicas := float64(currentReplicas) * reductionRatio * 0.9
			optimalReplicas = math.Floor(optimalReplicas)

			if optimalReplicas < float64(minReplicas) {
				optimalReplicas = float64(minReplicas)
			}

			return int32(optimalReplicas)
		}
		return minReplicas
	}

	scaleUpRatio := weightedLag / float64(targetLag)
	optimalReplicas := float64(currentReplicas) * scaleUpRatio
	optimalReplicas = math.Ceil(optimalReplicas)

	if optimalReplicas > float64(maxReplicas) {
		optimalReplicas = float64(maxReplicas)
	}

	return int32(optimalReplicas)
}

func (p *Predictor) PredictEnsembleWithProcessingTime(
	data []LagDataPoint,
	predictionWindow time.Duration,
	messageProcessingLatency time.Duration,
) *Prediction {
	if len(data) < 2 {
		return nil
	}

	processingRate, arrivalRate := p.calculateProcessingRates(data)

	basePrediction := p.PredictEnsemble(data, predictionWindow)
	if basePrediction == nil {
		basePrediction = &Prediction{
			PredictedLag: data[len(data)-1].Lag,
			Confidence:   0.5,
			Trend:        "stable",
			RateOfChange: 0,
		}
	}

	adjustedLag := p.adjustPredictionWithProcessingTime(
		basePrediction.PredictedLag,
		processingRate,
		arrivalRate,
		messageProcessingLatency,
		predictionWindow,
	)

	processTimePerMsg := time.Duration(0)
	if processingRate > 0 {
		processTimePerMsg = time.Duration(float64(time.Second) / processingRate)
	}

	trend := "stable"
	if arrivalRate > processingRate*1.1 {
		trend = "increasing"
	} else if arrivalRate < processingRate*0.9 {
		trend = "decreasing"
	}

	return &Prediction{
		PredictedLag:     adjustedLag,
		PredictionTime:   time.Now().Add(predictionWindow),
		Confidence:       basePrediction.Confidence,
		Trend:            trend,
		RateOfChange:     basePrediction.RateOfChange,
		Method:           "ensemble_with_processing_time",
		ProcessingRate:   processingRate,
		ArrivalRate:      arrivalRate,
		ProcessTimePerMsg: processTimePerMsg,
	}
}

func (p *Predictor) calculateProcessingRates(data []LagDataPoint) (processingRate float64, arrivalRate float64) {
	if len(data) < 5 {
		return 0, 0
	}

	recentData := data
	if len(data) > 20 {
		recentData = data[len(data)-20:]
	}

	var lagChanges []float64
	var timeIntervals []float64

	for i := 1; i < len(recentData); i++ {
		lagChange := float64(recentData[i].Lag - recentData[i-1].Lag)
		timeInterval := recentData[i].Timestamp.Sub(recentData[i-1].Timestamp).Seconds()

		if timeInterval > 0 {
			lagChanges = append(lagChanges, lagChange)
			timeIntervals = append(timeIntervals, timeInterval)
		}
	}

	if len(lagChanges) == 0 {
		return 0, 0
	}

	avgLagChange, _ := stats.Mean(lagChanges)
	avgTimeInterval, _ := stats.Mean(timeIntervals)

	if avgTimeInterval <= 0 {
		return 0, 0
	}

	netRate := avgLagChange / avgTimeInterval

	baseProcessingRate := 100.0
	arrivalRate = baseProcessingRate + netRate
	processingRate = baseProcessingRate

	if arrivalRate < 0 {
		arrivalRate = 0
	}
	if processingRate < 0 {
		processingRate = 0
	}

	p.logger.Debugf("Calculated rates: processing=%.2f msg/s, arrival=%.2f msg/s, net=%.2f msg/s",
		processingRate, arrivalRate, netRate)

	return processingRate, arrivalRate
}

func (p *Predictor) adjustPredictionWithProcessingTime(
	basePredictedLag int64,
	processingRate float64,
	arrivalRate float64,
	messageProcessingLatency time.Duration,
	predictionWindow time.Duration,
) int64 {
	if processingRate <= 0 || arrivalRate <= 0 {
		return basePredictedLag
	}

	predictionSeconds := predictionWindow.Seconds()
	processLatencySeconds := messageProcessingLatency.Seconds()

	if processLatencySeconds <= 0 {
		processLatencySeconds = 1.0
	}

	effectiveProcessingCapacity := processingRate / processLatencySeconds

	rateDifference := arrivalRate - effectiveProcessingCapacity

	var lagChange float64
	if rateDifference > 0 {
		lagChange = rateDifference * predictionSeconds
	} else if rateDifference < 0 {
		lagChange = rateDifference * predictionSeconds * 0.5
	} else {
		lagChange = 0
	}

	adjustedLag := float64(basePredictedLag) + lagChange

	if adjustedLag < 0 {
		adjustedLag = 0
	}

	p.logger.Debugf("Adjusted prediction: base=%d, rate_diff=%.2f, lag_change=%.2f, adjusted=%.0f",
		basePredictedLag, rateDifference, lagChange, adjustedLag)

	return int64(math.Round(adjustedLag))
}

func (p *Predictor) PredictWithQueueingTheory(
	data []LagDataPoint,
	predictionWindow time.Duration,
	messageProcessingLatency time.Duration,
) *Prediction {
	if len(data) < 2 {
		return nil
	}

	processingRate, arrivalRate := p.calculateProcessingRates(data)

	if processingRate <= 0 || arrivalRate <= 0 {
		return p.PredictEnsemble(data, predictionWindow)
	}

	utilization := arrivalRate / processingRate

	var predictedLag int64
	var trend string

	if utilization >= 1.0 {
		currentLag := data[len(data)-1].Lag
		lagGrowthRate := arrivalRate - processingRate
		predictedLag = currentLag + int64(lagGrowthRate*predictionWindow.Seconds())
		trend = "increasing"
	} else {
		avgLag := 0.0
		if processingRate > arrivalRate {
			avgServiceTime := 1.0 / processingRate
			avgLag = (utilization * avgServiceTime) / (1 - utilization)
		}
		predictedLag = int64(math.Round(avgLag * processingRate))
		trend = "stable"
	}

	if predictedLag < 0 {
		predictedLag = 0
	}

	processTimePerMsg := time.Duration(0)
	if processingRate > 0 {
		processTimePerMsg = time.Duration(float64(time.Second) / processingRate)
	}

	return &Prediction{
		PredictedLag:     predictedLag,
		PredictionTime:   time.Now().Add(predictionWindow),
		Confidence:       0.75,
		Trend:            trend,
		RateOfChange:     arrivalRate - processingRate,
		Method:           "queueing_theory",
		ProcessingRate:   processingRate,
		ArrivalRate:      arrivalRate,
		ProcessTimePerMsg: processTimePerMsg,
	}
}

func (p *Predictor) EstimateProcessingCapacity(
	data []LagDataPoint,
	currentReplicas int32,
) (float64, float64) {
	if len(data) < 5 || currentReplicas <= 0 {
		return 0, 0
	}

	processingRate, arrivalRate := p.calculateProcessingRates(data)

	perReplicaProcessing := processingRate / float64(currentReplicas)
	perReplicaArrival := arrivalRate / float64(currentReplicas)

	return perReplicaProcessing, perReplicaArrival
}

func (p *Predictor) PredictBacklogClearanceTime(
	data []LagDataPoint,
	currentReplicas int32,
	targetLag int64,
) (time.Duration, bool) {
	if len(data) < 2 {
		return 0, false
	}

	processingRate, arrivalRate := p.calculateProcessingRates(data)
	currentLag := data[len(data)-1].Lag

	if currentLag <= targetLag {
		return 0, true
	}

	netProcessingRate := processingRate - arrivalRate
	if netProcessingRate <= 0 {
		return 0, false
	}

	lagToClear := float64(currentLag - targetLag)
	secondsToClear := lagToClear / netProcessingRate

	return time.Duration(secondsToClear * float64(time.Second)), true
}
