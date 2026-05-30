package analysis

import (
	"fmt"
	"math"
	"time"

	"github.com/prometheus/downsampler/pkg/config"
	"github.com/prometheus/downsampler/pkg/prometheus"
)

type RecommendationEngine struct {
	cfg config.StrategyRecommendationConfig
}

func NewRecommendationEngine(cfg config.StrategyRecommendationConfig) *RecommendationEngine {
	return &RecommendationEngine{cfg: cfg}
}

type MetricFeatures struct {
	Name          string
	Labels        map[string]string
	Volatility    VolatilityMetrics
	SampleCount   int
	AnalysisPeriod time.Duration
	RawDataSize   int
}

type StrategyOption struct {
	Level          config.DownsamplingLevel
	Aggregations   []config.AggregationFunction
	EstimatedError float64
	EstimatedSaving float64
	Score          float64
}

func (re *RecommendationEngine) AnalyzeMetrics(series prometheus.TimeSeries) MetricFeatures {
	samples := series.Samples

	adaptive := NewAdaptiveEngine(config.AdaptiveDownsamplingConfig{
		VolatilityThreshold: 0.5,
		MinWindow:           time.Minute,
		MaxWindow:           time.Hour,
	})

	volatility := adaptive.CalculateVolatility(samples)

	return MetricFeatures{
		Name:           series.Labels["__name__"],
		Labels:         series.Labels,
		Volatility:     volatility,
		SampleCount:    len(samples),
		AnalysisPeriod: re.cfg.AnalyzePeriod,
		RawDataSize:    len(samples),
	}
}

func (re *RecommendationEngine) GenerateRecommendations(features MetricFeatures) []Recommendation {
	var recommendations []Recommendation

	levels := []config.DownsamplingLevel{
		config.LevelMinute,
		config.Level5Minutes,
		config.Level15Minutes,
		config.LevelHour,
		config.Level6Hours,
		config.LevelDay,
	}

	aggs := []config.AggregationFunction{
		config.AggAvg,
		config.AggMax,
		config.AggMin,
	}

	for _, level := range levels {
		estimatedError := re.estimateError(features, level)
		estimatedSaving := re.estimateSaving(features, level)

		if estimatedError > re.cfg.TargetErrorThreshold*100 {
			continue
		}

		score := re.calculateScore(estimatedError, estimatedSaving)

		var reasoning string
		switch {
		case features.Volatility.Volatility < 0.3:
			reasoning = fmt.Sprintf("低波动指标 (%.2f)，适合使用 %s 级别降采样",
				features.Volatility.Volatility, level)
		case features.Volatility.Volatility < 0.7:
			reasoning = fmt.Sprintf("中等波动指标 (%.2f)，推荐 %s 级别配合自适应调整",
				features.Volatility.Volatility, level)
		default:
			reasoning = fmt.Sprintf("高波动指标 (%.2f)，建议使用 %s 级别并保留峰值",
				features.Volatility.Volatility, level)
		}

		enableAdaptive := features.Volatility.Volatility > 0.5
		preservePeaks := features.Volatility.Volatility > 0.3 || features.Volatility.Skewness > 1.0
		preserveOutliers := features.Volatility.Kurtosis > 3.0 || features.Volatility.Range > features.Volatility.StdDev*4

		rec := Recommendation{
			MetricName:        features.Name,
			Labels:            features.Labels,
			RecommendedLevels: []config.DownsamplingLevel{level},
			RecommendedAggs:   aggs,
			EstimatedError:    estimatedError,
			EstimatedSaving:   estimatedSaving,
			Score:             score,
			Reasoning:         reasoning,
			AnalysisPeriod:    features.AnalysisPeriod,
			SampleCount:       features.SampleCount,
			Volatility:        features.Volatility.Volatility,
			AdaptiveEnabled:   enableAdaptive,
			AdaptiveHighLevel: config.LevelMinute,
			AdaptiveLowLevel:  level,
			PreservePeaks:     preservePeaks,
			PreserveOutliers:  preserveOutliers,
		}

		recommendations = append(recommendations, rec)
	}

	for i := range recommendations {
		for j := i + 1; j < len(recommendations); j++ {
			if recommendations[j].Score > recommendations[i].Score {
				recommendations[i], recommendations[j] = recommendations[j], recommendations[i]
			}
		}
	}

	return recommendations
}

func (re *RecommendationEngine) GetBestRecommendation(features MetricFeatures) *Recommendation {
	recs := re.GenerateRecommendations(features)
	if len(recs) == 0 {
		return nil
	}

	best := &recs[0]

	if len(recs) > 1 {
		best.RecommendedLevels = append(best.RecommendedLevels, recs[1].RecommendedLevels...)
	}

	return best
}

func (re *RecommendationEngine) estimateError(features MetricFeatures, level config.DownsamplingLevel) float64 {
	levelDurations := map[config.DownsamplingLevel]time.Duration{
		config.LevelMinute:     time.Minute,
		config.Level5Minutes:   5 * time.Minute,
		config.Level15Minutes:  15 * time.Minute,
		config.LevelHour:       time.Hour,
		config.Level6Hours:     6 * time.Hour,
		config.LevelDay:        24 * time.Hour,
	}

	duration, ok := levelDurations[level]
	if !ok {
		duration = time.Minute
	}

	compressionRatio := float64(duration) / float64(15*time.Second)

	baseError := math.Log10(compressionRatio) * 2

	volatilityFactor := features.Volatility.Volatility * 10

	cvFactor := features.Volatility.CV * 5

	estimatedError := baseError + volatilityFactor + cvFactor

	return math.Max(0, estimatedError)
}

func (re *RecommendationEngine) estimateSaving(features MetricFeatures, level config.DownsamplingLevel) float64 {
	levelDurations := map[config.DownsamplingLevel]time.Duration{
		config.LevelMinute:     time.Minute,
		config.Level5Minutes:   5 * time.Minute,
		config.Level15Minutes:  15 * time.Minute,
		config.LevelHour:       time.Hour,
		config.Level6Hours:     6 * time.Hour,
		config.LevelDay:        24 * time.Hour,
	}

	duration, ok := levelDurations[level]
	if !ok {
		duration = time.Minute
	}

	originalPoints := float64(features.AnalysisPeriod) / float64(15*time.Second)
	downsampledPoints := float64(features.AnalysisPeriod) / float64(duration)

	saving := 1.0 - (downsampledPoints / originalPoints)

	return saving * 100
}

func (re *RecommendationEngine) calculateScore(errorPct, savingPct float64) float64 {
	normalizedError := 1.0 - math.Min(errorPct/100.0, 1.0)
	normalizedSaving := savingPct / 100.0

	score := normalizedError*re.cfg.AccuracyWeight + normalizedSaving*re.cfg.StorageCostWeight

	return score * 100
}

func (re *RecommendationEngine) GenerateConfigFromRecommendation(rec *Recommendation) config.MetricRule {
	if rec == nil {
		return config.MetricRule{}
	}

	rule := config.MetricRule{
		Name:               fmt.Sprintf("auto_%s", rec.MetricName),
		Match:              fmt.Sprintf(`{__name__="%s"}`, rec.MetricName),
		Aggregations:       rec.RecommendedAggs,
		DownsamplingLevels: rec.RecommendedLevels,
		AlignToBoundary:    true,
		PreservePeaks: config.PeakDetectionConfig{
			Enabled:         rec.PreservePeaks,
			ZScoreThreshold: 3.0,
			Percentile:      99.0,
		},
		PreserveOutliers: config.OutlierDetectionConfig{
			Enabled:       rec.PreserveOutliers,
			IQRMultiplier: 1.5,
			PreserveCount: 5,
		},
		AdaptiveDownsampling: config.AdaptiveDownsamplingConfig{
			Enabled:            rec.AdaptiveEnabled,
			VolatilityThreshold: 0.5,
			MinWindow:          time.Minute,
			MaxWindow:          time.Hour,
			HighVolatilityLevel: rec.AdaptiveHighLevel,
			LowVolatilityLevel:  rec.AdaptiveLowLevel,
		},
		ErrorAnalysis: config.ErrorAnalysisConfig{
			Enabled:       true,
			CalculateMAE:  true,
			CalculateRMSE: true,
			CalculateMAPE: true,
		},
	}

	return rule
}

func (re *RecommendationEngine) BatchAnalyze(seriesList []prometheus.TimeSeries) []Recommendation {
	var allRecs []Recommendation

	for _, series := range seriesList {
		if len(series.Samples) < re.cfg.MinSamples {
			continue
		}

		features := re.AnalyzeMetrics(series)
		best := re.GetBestRecommendation(features)
		if best != nil {
			allRecs = append(allRecs, *best)
		}
	}

	return allRecs
}

func GenerateRecommendationReport(recs []Recommendation) string {
	if len(recs) == 0 {
		return "No recommendations available."
	}

	report := "=== 降采样策略推荐报告 ===\n\n"

	for i, rec := range recs {
		report += fmt.Sprintf("排名 %d: %s\n", i+1, rec.MetricName)
		report += fmt.Sprintf("  推荐级别: %v\n", rec.RecommendedLevels)
		report += fmt.Sprintf("  推荐聚合: %v\n", rec.RecommendedAggs)
		report += fmt.Sprintf("  预计误差: %.2f%%\n", rec.EstimatedError)
		report += fmt.Sprintf("  预计节省: %.2f%%\n", rec.EstimatedSaving)
		report += fmt.Sprintf("  综合得分: %.2f\n", rec.Score)
		report += fmt.Sprintf("  波动性: %.2f\n", rec.Volatility)
		report += fmt.Sprintf("  自适应: %v\n", rec.AdaptiveEnabled)
		report += fmt.Sprintf("  峰值保留: %v\n", rec.PreservePeaks)
		report += fmt.Sprintf("  异常保留: %v\n", rec.PreserveOutliers)
		report += fmt.Sprintf("  分析说明: %s\n\n", rec.Reasoning)
	}

	return report
}
