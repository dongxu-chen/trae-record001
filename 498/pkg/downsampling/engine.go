package downsampling

import (
	"fmt"
	"math"
	"sort"
	"strings"
	"time"

	"github.com/prometheus/downsampler/pkg/analysis"
	"github.com/prometheus/downsampler/pkg/config"
	"github.com/prometheus/downsampler/pkg/prometheus"
)

type Aggregator interface {
	Aggregate(values []float64) float64
}

type AvgAggregator struct{}

func (a *AvgAggregator) Aggregate(values []float64) float64 {
	if len(values) == 0 {
		return math.NaN()
	}
	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum / float64(len(values))
}

type MaxAggregator struct{}

func (a *MaxAggregator) Aggregate(values []float64) float64 {
	if len(values) == 0 {
		return math.NaN()
	}
	max := values[0]
	for _, v := range values[1:] {
		if v > max {
			max = v
		}
	}
	return max
}

type MinAggregator struct{}

func (a *MinAggregator) Aggregate(values []float64) float64 {
	if len(values) == 0 {
		return math.NaN()
	}
	min := values[0]
	for _, v := range values[1:] {
		if v < min {
			min = v
		}
	}
	return min
}

type SumAggregator struct{}

func (a *SumAggregator) Aggregate(values []float64) float64 {
	if len(values) == 0 {
		return math.NaN()
	}
	sum := 0.0
	for _, v := range values {
		sum += v
	}
	return sum
}

type CountAggregator struct{}

func (a *CountAggregator) Aggregate(values []float64) float64 {
	return float64(len(values))
}

type PercentileAggregator struct {
	Percentile float64
}

func (a *PercentileAggregator) Aggregate(values []float64) float64 {
	if len(values) == 0 {
		return math.NaN()
	}
	sorted := make([]float64, len(values))
	copy(sorted, values)
	sort.Float64s(sorted)

	rank := (a.Percentile / 100.0) * float64(len(sorted)-1)
	idx := int(rank)
	frac := rank - float64(idx)

	if idx >= len(sorted)-1 {
		return sorted[len(sorted)-1]
	}

	return sorted[idx] + frac*(sorted[idx+1]-sorted[idx])
}

func NewAggregator(fn config.AggregationFunction) (Aggregator, error) {
	switch fn {
	case config.AggAvg:
		return &AvgAggregator{}, nil
	case config.AggMax:
		return &MaxAggregator{}, nil
	case config.AggMin:
		return &MinAggregator{}, nil
	case config.AggSum:
		return &SumAggregator{}, nil
	case config.AggCount:
		return &CountAggregator{}, nil
	case config.AggP50:
		return &PercentileAggregator{Percentile: 50}, nil
	case config.AggP90:
		return &PercentileAggregator{Percentile: 90}, nil
	case config.AggP95:
		return &PercentileAggregator{Percentile: 95}, nil
	case config.AggP99:
		return &PercentileAggregator{Percentile: 99}, nil
	default:
		return nil, fmt.Errorf("unsupported aggregation function: %s", fn)
	}
}

type PointType string

const (
	PointTypeAggregated PointType = "aggregated"
	PointTypePeak       PointType = "peak"
	PointTypeOutlier    PointType = "outlier"
)

type DownsampledPoint struct {
	Timestamp    time.Time
	Value        float64
	Level        config.DownsamplingLevel
	Aggregation  config.AggregationFunction
	OriginalName string
	Labels       map[string]string
	PointType    PointType
	RawTimestamp time.Time
	RawValue     float64
}

type Engine struct {
	namespace       string
	adaptiveEngine  *analysis.AdaptiveEngine
	errorAnalyzer   *analysis.ErrorAnalyzer
	recommendationEngine *analysis.RecommendationEngine
}

func NewEngine(namespace string) *Engine {
	return &Engine{
		namespace: namespace,
	}
}

func (e *Engine) InitAdaptive(cfg config.AdaptiveDownsamplingConfig) {
	e.adaptiveEngine = analysis.NewAdaptiveEngine(cfg)
}

func (e *Engine) InitErrorAnalysis(cfg config.ErrorAnalysisConfig) {
	e.errorAnalyzer = analysis.NewErrorAnalyzer(cfg)
}

func (e *Engine) InitRecommendation(cfg config.StrategyRecommendationConfig) {
	e.recommendationEngine = analysis.NewRecommendationEngine(cfg)
}

func (e *Engine) GetAdaptiveEngine() *analysis.AdaptiveEngine {
	return e.adaptiveEngine
}

func (e *Engine) GetErrorAnalyzer() *analysis.ErrorAnalyzer {
	return e.errorAnalyzer
}

func (e *Engine) GetRecommendationEngine() *analysis.RecommendationEngine {
	return e.recommendationEngine
}

func (e *Engine) Downsample(
	series prometheus.TimeSeries,
	rule config.MetricRule,
	start, end time.Time,
) ([]DownsampledPoint, error) {
	if len(series.Samples) == 0 {
		return nil, nil
	}

	var allPoints []DownsampledPoint

	levels := rule.DownsamplingLevels

	if rule.AdaptiveDownsampling.Enabled && e.adaptiveEngine != nil {
		levels = e.getAdaptiveLevels(series, rule)
	}

	for _, level := range levels {
		window, err := level.Duration()
		if err != nil {
			return nil, err
		}
		if window == 0 {
			continue
		}

		for _, aggFn := range rule.Aggregations {
			agg, err := NewAggregator(aggFn)
			if err != nil {
				return nil, err
			}

			points, err := e.downsampleLevel(series, rule, level, window, agg, aggFn, start, end)
			if err != nil {
				return nil, err
			}
			allPoints = append(allPoints, points...)
		}
	}

	return allPoints, nil
}

func (e *Engine) getAdaptiveLevels(series prometheus.TimeSeries, rule config.MetricRule) []config.DownsamplingLevel {
	if e.adaptiveEngine == nil {
		return rule.DownsamplingLevels
	}

	result := e.adaptiveEngine.Adapt(series.Samples, 0)

	var levels []config.DownsamplingLevel

	highDuration := e.adaptiveEngine.GetLevelDuration(result.Window.Level)
	lowDuration := e.adaptiveEngine.GetLevelDuration(rule.AdaptiveDownsampling.LowVolatilityLevel)

	if highDuration < lowDuration {
		levels = append(levels, result.Window.Level)
	}

	found := false
	for _, l := range rule.DownsamplingLevels {
		if l == result.Window.Level {
			found = true
		}
	}
	if !found {
		levels = append(levels, rule.DownsamplingLevels...)
	} else {
		levels = append(levels, rule.DownsamplingLevels...)
	}

	return uniqueLevels(levels)
}

func uniqueLevels(levels []config.DownsamplingLevel) []config.DownsamplingLevel {
	seen := make(map[config.DownsamplingLevel]bool)
	var result []config.DownsamplingLevel
	for _, l := range levels {
		if !seen[l] {
			seen[l] = true
			result = append(result, l)
		}
	}
	return result
}

func (e *Engine) EvaluateDownsampling(
	original []prometheus.Sample,
	downsampled []DownsampledPoint,
) analysis.ErrorMetrics {
	if e.errorAnalyzer == nil {
		return analysis.ErrorMetrics{}
	}

	analysisPoints := make([]analysis.DownsampledPoint, len(downsampled))
	for i, p := range downsampled {
		analysisPoints[i] = analysis.DownsampledPoint{
			Timestamp:     p.Timestamp,
			Value:         p.Value,
			Labels:        p.Labels,
			Aggregation:   p.Aggregation,
			Level:         p.Level,
			PointType:     analysis.PointType(p.PointType),
		}
	}

	return e.errorAnalyzer.Analyze(original, analysisPoints)
}

func (e *Engine) RecommendStrategy(series prometheus.TimeSeries) *analysis.Recommendation {
	if e.recommendationEngine == nil {
		return nil
	}

	features := e.recommendationEngine.AnalyzeMetrics(series)
	return e.recommendationEngine.GetBestRecommendation(features)
}

func (e *Engine) alignToBoundary(t time.Time, window time.Duration) time.Time {
	return t.Truncate(window)
}

type bucketData struct {
	values    []float64
	samples   []prometheus.Sample
}

func (e *Engine) downsampleLevel(
	series prometheus.TimeSeries,
	rule config.MetricRule,
	level config.DownsamplingLevel,
	window time.Duration,
	agg Aggregator,
	aggFn config.AggregationFunction,
	start, end time.Time,
) ([]DownsampledPoint, error) {
	buckets := make(map[time.Time]*bucketData)

	alignedStart := e.alignToBoundary(start, window)
	alignedEnd := e.alignToBoundary(end, window)

	for _, sample := range series.Samples {
		if sample.Timestamp.Before(alignedStart) || sample.Timestamp.After(alignedEnd) {
			continue
		}

		bucketTime := e.alignToBoundary(sample.Timestamp, window)
		if _, exists := buckets[bucketTime]; !exists {
			buckets[bucketTime] = &bucketData{}
		}
		buckets[bucketTime].values = append(buckets[bucketTime].values, sample.Value)
		buckets[bucketTime].samples = append(buckets[bucketTime].samples, sample)
	}

	labels := e.processLabels(series.Labels, rule)

	var points []DownsampledPoint

	for bucketTime, data := range buckets {
		aggValue := agg.Aggregate(data.values)
		if math.IsNaN(aggValue) {
			continue
		}

		pointLabels := make(map[string]string, len(labels)+2)
		for k, v := range labels {
			pointLabels[k] = v
		}
		pointLabels["ds_level"] = string(level)
		pointLabels["ds_agg"] = string(aggFn)
		pointLabels["ds_type"] = string(PointTypeAggregated)

		points = append(points, DownsampledPoint{
			Timestamp:    bucketTime,
			Value:        aggValue,
			Level:        level,
			Aggregation:  aggFn,
			OriginalName: series.Labels["__name__"],
			Labels:       pointLabels,
			PointType:    PointTypeAggregated,
		})

		if rule.PreservePeaks.Enabled {
			peakPoints := e.detectAndSavePeaks(data.samples, bucketTime, level, aggFn, series.Labels["__name__"], labels, rule)
			points = append(points, peakPoints...)
		}

		if rule.PreserveOutliers.Enabled {
			outlierPoints := e.detectAndSaveOutliers(data.samples, bucketTime, level, aggFn, series.Labels["__name__"], labels, rule)
			points = append(points, outlierPoints...)
		}
	}

	sort.Slice(points, func(i, j int) bool {
		return points[i].Timestamp.Before(points[j].Timestamp)
	})

	return points, nil
}

func (e *Engine) detectAndSavePeaks(
	samples []prometheus.Sample,
	bucketTime time.Time,
	level config.DownsamplingLevel,
	aggFn config.AggregationFunction,
	originalName string,
	baseLabels map[string]string,
	rule config.MetricRule,
) []DownsampledPoint {
	if len(samples) < 3 {
		return nil
	}

	values := make([]float64, len(samples))
	for i, s := range samples {
		values[i] = s.Value
	}

	mean, stdDev := e.calculateMeanAndStdDev(values)
	if stdDev == 0 {
		return nil
	}

	var peaks []DownsampledPoint
	threshold := rule.PreservePeaks.ZScoreThreshold

	for i := 1; i < len(samples)-1; i++ {
		zScore := (samples[i].Value - mean) / stdDev
		if math.Abs(zScore) >= threshold {
			if samples[i].Value > samples[i-1].Value && samples[i].Value > samples[i+1].Value {
				pointLabels := make(map[string]string, len(baseLabels)+4)
				for k, v := range baseLabels {
					pointLabels[k] = v
				}
				pointLabels["ds_level"] = string(level)
				pointLabels["ds_agg"] = string(aggFn)
				pointLabels["ds_type"] = string(PointTypePeak)
				pointLabels["ds_zscore"] = fmt.Sprintf("%.2f", zScore)

				peaks = append(peaks, DownsampledPoint{
					Timestamp:    bucketTime,
					Value:      samples[i].Value,
					Level:      level,
					Aggregation:  aggFn,
					OriginalName: originalName,
					Labels:     pointLabels,
					PointType:  PointTypePeak,
					RawTimestamp: samples[i].Timestamp,
					RawValue:   samples[i].Value,
				})
			}
		}
	}

	return peaks
}

func (e *Engine) detectAndSaveOutliers(
	samples []prometheus.Sample,
	bucketTime time.Time,
	level config.DownsamplingLevel,
	aggFn config.AggregationFunction,
	originalName string,
	baseLabels map[string]string,
	rule config.MetricRule,
) []DownsampledPoint {
	if len(samples) < 4 {
		return nil
	}

	values := make([]float64, len(samples))
	for i, s := range samples {
		values[i] = s.Value
	}
	sort.Float64s(values)

	q1 := e.percentile(values, 25)
	q3 := e.percentile(values, 75)
	iqr := q3 - q1
	lowerBound := q1 - rule.PreserveOutliers.IQRMultiplier*iqr
	upperBound := q3 + rule.PreserveOutliers.IQRMultiplier*iqr

	var outliers []prometheus.Sample
	for _, s := range samples {
		if s.Value < lowerBound || s.Value > upperBound {
			outliers = append(outliers, s)
		}
	}

	if len(outliers) > rule.PreserveOutliers.PreserveCount {
		sort.Slice(outliers, func(i, j int) bool {
			distI := math.Abs(outliers[i].Value - (q1+q3)/2)
			distJ := math.Abs(outliers[j].Value - (q1+q3)/2)
			return distI > distJ
		})
		outliers = outliers[:rule.PreserveOutliers.PreserveCount]
	}

	var points []DownsampledPoint
	for _, s := range outliers {
		pointLabels := make(map[string]string, len(baseLabels)+3)
		for k, v := range baseLabels {
			pointLabels[k] = v
		}
		pointLabels["ds_level"] = string(level)
		pointLabels["ds_agg"] = string(aggFn)
		pointLabels["ds_type"] = string(PointTypeOutlier)

		points = append(points, DownsampledPoint{
			Timestamp:    bucketTime,
			Value:      s.Value,
			Level:      level,
			Aggregation:  aggFn,
			OriginalName: originalName,
			Labels:     pointLabels,
			PointType:  PointTypeOutlier,
			RawTimestamp: s.Timestamp,
			RawValue:   s.Value,
		})
	}

	return points
}

func (e *Engine) calculateMeanAndStdDev(values []float64) (float64, float64) {
	if len(values) == 0 {
		return 0, 0
	}

	sum := 0.0
	for _, v := range values {
		sum += v
	}
	mean := sum / float64(len(values))

	variance := 0.0
	for _, v := range values {
		diff := v - mean
		variance += diff * diff
	}
	variance /= float64(len(values))

	return mean, math.Sqrt(variance)
}

func (e *Engine) percentile(values []float64, p float64) float64 {
	if len(values) == 0 {
		return 0
	}
	if len(values) == 1 {
		return values[0]
	}

	index := (p / 100.0) * float64(len(values)-1)
	i := int(index)
	frac := index - float64(i)

	if i >= len(values)-1 {
		return values[len(values)-1]
	}

	return values[i] + frac*(values[i+1]-values[i])
}

func (e *Engine) processLabels(labels map[string]string, rule config.MetricRule) map[string]string {
	result := make(map[string]string)

	for k, v := range labels {
		if k == "__name__" {
			continue
		}

		if len(rule.PreserveLabels) > 0 {
			preserved := false
			for _, p := range rule.PreserveLabels {
				if k == p {
					preserved = true
					break
				}
			}
			if !preserved {
				continue
			}
		}

		if len(rule.DropLabels) > 0 {
			dropped := false
			for _, d := range rule.DropLabels {
				if k == d {
					dropped = true
					break
				}
			}
			if dropped {
				continue
			}
		}

		result[k] = v
	}

	return result
}

func (e *Engine) GenerateMetricName(originalName string, aggFn config.AggregationFunction, level config.DownsamplingLevel) string {
	parts := []string{e.namespace}
	if originalName != "" {
		parts = append(parts, originalName)
	}
	parts = append(parts, string(aggFn), string(level))
	return strings.Join(parts, ":")
}

func (p *DownsampledPoint) GetMetricName(namespace string) string {
	parts := []string{namespace}
	if p.OriginalName != "" {
		parts = append(parts, p.OriginalName)
	}
	parts = append(parts, string(p.Aggregation), string(p.Level))
	return strings.Join(parts, ":")
}

type BatchResult struct {
	RuleName   string
	Points     []DownsampledPoint
	InputCount int
	OutputCount int
	Error      error
}

func (e *Engine) ProcessQueryResult(
	result *prometheus.QueryResult,
	rule config.MetricRule,
	start, end time.Time,
) *BatchResult {
	batch := &BatchResult{
		RuleName: rule.Name,
	}

	if result == nil || len(result.Series) == 0 {
		return batch
	}

	batch.InputCount = 0
	for _, series := range result.Series {
		batch.InputCount += len(series.Samples)
	}

	for _, series := range result.Series {
		points, err := e.Downsample(series, rule, start, end)
		if err != nil {
			batch.Error = err
			return batch
		}
		batch.Points = append(batch.Points, points...)
	}

	batch.OutputCount = len(batch.Points)
	return batch
}
