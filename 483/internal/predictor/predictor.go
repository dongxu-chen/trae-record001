package predictor

import (
	"math"
	"sort"
	"strconv"
	"time"

	"kafka-lag-analyzer/internal/analyzer"
	"kafka-lag-analyzer/internal/config"
)

type Predictor interface {
	PredictGroupProgress(groupID string, analysis *analyzer.ConsumerGroupAnalysis, historyFunc func(string, string, int32) []analyzer.HistoricalLag) (*analyzer.GroupProgressPrediction, error)
}

type progressPredictor struct {
	cfg *config.AnalyzerConfig
	forecastCfg analyzer.ForecastConfig
}

func NewPredictor(cfg *config.AnalyzerConfig) Predictor {
	return &progressPredictor{
		cfg: cfg,
		forecastCfg: analyzer.ForecastConfig{
			PredictionHorizon:     24 * time.Hour,
			PredictionInterval:    15 * time.Minute,
			MinDataPoints:         5,
			RateCalculationWindow: 10,
			UseWeightedRegression: true,
			ConfidenceThreshold:   0.7,
		},
	}
}

func (p *progressPredictor) PredictGroupProgress(
	groupID string,
	analysis *analyzer.ConsumerGroupAnalysis,
	historyFunc func(string, string, int32) []analyzer.HistoricalLag,
) (*analyzer.GroupProgressPrediction, error) {
	if analysis == nil {
		return nil, nil
	}

	prediction := &analyzer.GroupProgressPrediction{
		GroupID:             groupID,
		TotalLag:            analysis.TotalLag,
		PartitionPredictions: make(map[string]map[int32]analyzer.ProgressPrediction),
	}

	var totalConsumptionRate float64
	var totalIngestionRate float64
	var totalConfidence float64
	var predictionCount int
	var maxTimeToClear time.Duration

	for topic, topicLag := range analysis.Topics {
		if _, ok := prediction.PartitionPredictions[topic]; !ok {
			prediction.PartitionPredictions[topic] = make(map[int32]analyzer.ProgressPrediction)
		}

		for _, partLag := range topicLag.Partitions {
			history := historyFunc(groupID, topic, partLag.Partition)
			partPred := p.predictPartitionProgress(partLag, history)

			prediction.PartitionPredictions[topic][partLag.Partition] = partPred

			totalConsumptionRate += partPred.ConsumptionRate
			totalIngestionRate += partPred.IngestionRate
			totalConfidence += partPred.Confidence
			predictionCount++

			if partPred.EstimatedTimeToClear > maxTimeToClear {
				maxTimeToClear = partPred.EstimatedTimeToClear
			}

			if partPred.EstimatedTimeToClear > 1*time.Hour && partPred.Lag > p.cfg.LagThreshold {
				prediction.CriticalPartitions = append(
					prediction.CriticalPartitions,
					topic+"-"+strconv.Itoa(int(partLag.Partition)),
				)
			}
		}
	}

	if predictionCount > 0 {
		prediction.AggregateConsumptionRate = totalConsumptionRate / float64(predictionCount)
		prediction.AggregateIngestionRate = totalIngestionRate / float64(predictionCount)
		prediction.Confidence = totalConfidence / float64(predictionCount)
		prediction.OverallEstimatedTimeToClear = maxTimeToClear
	}

	sort.Slice(prediction.CriticalPartitions, func(i, j int) bool {
		return prediction.CriticalPartitions[i] < prediction.CriticalPartitions[j]
	})

	return prediction, nil
}

func (p *progressPredictor) predictPartitionProgress(
	partLag analyzer.PartitionLag,
	history []analyzer.HistoricalLag,
) analyzer.ProgressPrediction {
	pred := analyzer.ProgressPrediction{
		Topic:      partLag.Topic,
		Partition:  partLag.Partition,
		CurrentLag: partLag.Lag,
		WillCatchUp: false,
	}

	if len(history) < p.forecastCfg.MinDataPoints {
		pred.Confidence = 0.3
		pred.PredictionMethod = "insufficient_data"
		pred.EstimatedTimeToClear = time.Duration(math.MaxInt64)
		return pred
	}

	windowSize := p.forecastCfg.RateCalculationWindow
	if windowSize > len(history) {
		windowSize = len(history)
	}
	recent := history[len(history)-windowSize:]

	consumptionRate, consR2 := p.linearRegressionRate(recent, func(h analyzer.HistoricalLag) float64 {
		return float64(h.Offset)
	})

	ingestionRate, ingR2 := p.linearRegressionRate(recent, func(h analyzer.HistoricalLag) float64 {
		return float64(h.EndOffset)
	})

	netRate := consumptionRate - ingestionRate
	pred.ConsumptionRate = math.Max(0, consumptionRate)
	pred.IngestionRate = math.Max(0, ingestionRate)
	pred.NetRate = netRate

	pred.Confidence = (math.Abs(consR2) + math.Abs(ingR2)) / 2.0
	if pred.Confidence > 1.0 {
		pred.Confidence = 1.0
	}

	if consumptionRate <= 0 || partLag.Lag == 0 {
		pred.PredictionMethod = "no_progress"
		pred.EstimatedTimeToClear = time.Duration(math.MaxInt64)
		pred.WillCatchUp = false
		return pred
	}

	pred.TimeToCatchUpAtRate = time.Duration(float64(partLag.Lag)/consumptionRate) * time.Second

	if netRate > 0 {
		pred.WillCatchUp = true
		pred.EstimatedTimeToClear = time.Duration(float64(partLag.Lag)/netRate) * time.Second
		pred.PredictionMethod = "positive_net_rate"
	} else if math.Abs(netRate) < 0.001 {
		pred.WillCatchUp = true
		pred.EstimatedTimeToClear = pred.TimeToCatchUpAtRate
		pred.PredictionMethod = "stable_rate"
	} else {
		pred.WillCatchUp = false
		pred.EstimatedTimeToClear = time.Duration(math.MaxInt64)
		pred.PredictionMethod = "growing_lag"
	}

	pred.PredictionPoints = p.generatePredictionPoints(partLag, recent, consumptionRate, ingestionRate)

	return pred
}

func (p *progressPredictor) linearRegressionRate(
	data []analyzer.HistoricalLag,
	valueFunc func(analyzer.HistoricalLag) float64,
) (float64, float64) {
	n := len(data)
	if n < 2 {
		return 0, 0
	}

	var sumX, sumY, sumXY, sumX2, sumY2 float64
	startTime := data[0].Timestamp

	weights := make([]float64, n)
	if p.forecastCfg.UseWeightedRegression {
		for i := range data {
			weights[i] = float64(i+1) / float64(n*(n+1)/2)
		}
	} else {
		for i := range weights {
			weights[i] = 1.0 / float64(n)
		}
	}

	totalWeight := 0.0
	for _, w := range weights {
		totalWeight += w
	}

	for i, point := range data {
		x := point.Timestamp.Sub(startTime).Seconds()
		y := valueFunc(point)
		w := weights[i]

		sumX += x * w
		sumY += y * w
		sumXY += x * y * w
		sumX2 += x * x * w
		sumY2 += y * y * w
	}

	denominator := sumX2 - sumX*sumX/totalWeight
	if math.Abs(denominator) < 1e-10 {
		return 0, 0
	}

	slope := (sumXY - sumX*sumY/totalWeight) / denominator

	ssTotal := sumY2 - sumY*sumY/totalWeight
	ssResidual := ssTotal - slope*slope*denominator

	r2 := 1.0
	if ssTotal > 1e-10 {
		r2 = 1.0 - ssResidual/ssTotal
	}
	if r2 < 0 {
		r2 = 0
	}

	return slope, r2
}

func (p *progressPredictor) generatePredictionPoints(
	partLag analyzer.PartitionLag,
	history []analyzer.HistoricalLag,
	consumptionRate float64,
	ingestionRate float64,
) []analyzer.PredictionPoint {
	if len(history) == 0 {
		return nil
	}

	points := make([]analyzer.PredictionPoint, 0)
	now := time.Now()
	lastHist := history[len(history)-1]
	currentOffset := lastHist.Offset
	currentEndOffset := lastHist.EndOffset

	for t := p.forecastCfg.PredictionInterval;
		t <= p.forecastCfg.PredictionHorizon;
		t += p.forecastCfg.PredictionInterval {

		projectedOffset := currentOffset + int64(consumptionRate*t.Seconds())
		projectedEndOffset := currentEndOffset + int64(ingestionRate*t.Seconds())
		projectedLag := projectedEndOffset - projectedOffset

		if projectedLag < 0 {
			projectedLag = 0
		}

		points = append(points, analyzer.PredictionPoint{
			Timestamp:      now.Add(t),
			ProjectedLag:   projectedLag,
			ProjectedOffset: projectedOffset,
		})

		if projectedLag == 0 {
			break
		}
	}

	return points
}

func FormatDuration(d time.Duration) string {
	if d == time.Duration(math.MaxInt64) || d < 0 {
		return "无法预估"
	}

	days := int(d.Hours()) / 24
	hours := int(d.Hours()) % 24
	minutes := int(d.Minutes()) % 60

	result := ""
	if days > 0 {
		result += strconv.Itoa(days) + "天"
	}
	if hours > 0 || days > 0 {
		result += strconv.Itoa(hours) + "小时"
	}
	if minutes > 0 || hours > 0 || days > 0 {
		result += strconv.Itoa(minutes) + "分钟"
	}

	if result == "" {
		result = "< 1分钟"
	}
	return result
}
