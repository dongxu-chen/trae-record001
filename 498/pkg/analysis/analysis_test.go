package analysis

import (
	"math"
	"testing"
	"time"

	"github.com/prometheus/downsampler/pkg/config"
	"github.com/prometheus/downsampler/pkg/prometheus"
)

func TestCalculateVolatility(t *testing.T) {
	cfg := config.AdaptiveDownsamplingConfig{
		VolatilityThreshold: 0.5,
		MinWindow:           time.Minute,
		MaxWindow:           time.Hour,
	}
	engine := NewAdaptiveEngine(cfg)

	baseTime := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)

	t.Run("low volatility", func(t *testing.T) {
		samples := make([]prometheus.Sample, 20)
		for i := 0; i < 20; i++ {
			samples[i] = prometheus.Sample{
				Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
				Value:     10.0 + float64(i)*0.01,
			}
		}

		vol := engine.CalculateVolatility(samples)
		if vol.Volatility >= 0.5 {
			t.Errorf("Expected low volatility, got %.4f", vol.Volatility)
		}
		t.Logf("Low volatility: %.4f", vol.Volatility)
	})

	t.Run("high volatility", func(t *testing.T) {
		samples := make([]prometheus.Sample, 20)
		for i := 0; i < 20; i++ {
			val := 10.0
			if i%2 == 0 {
				val = 100.0
			}
			samples[i] = prometheus.Sample{
				Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
				Value:     val,
			}
		}

		vol := engine.CalculateVolatility(samples)
		if vol.Volatility < 0.5 {
			t.Errorf("Expected high volatility, got %.4f", vol.Volatility)
		}
		t.Logf("High volatility: %.4f", vol.Volatility)
	})

	t.Run("basic statistics", func(t *testing.T) {
		samples := []prometheus.Sample{
			{Timestamp: baseTime, Value: 1},
			{Timestamp: baseTime.Add(15 * time.Second), Value: 2},
			{Timestamp: baseTime.Add(30 * time.Second), Value: 3},
			{Timestamp: baseTime.Add(45 * time.Second), Value: 4},
			{Timestamp: baseTime.Add(60 * time.Second), Value: 5},
		}

		vol := engine.CalculateVolatility(samples)

		if vol.MeanValue != 3.0 {
			t.Errorf("Expected mean 3.0, got %.2f", vol.MeanValue)
		}
		if vol.MinValue != 1.0 {
			t.Errorf("Expected min 1.0, got %.2f", vol.MinValue)
		}
		if vol.MaxValue != 5.0 {
			t.Errorf("Expected max 5.0, got %.2f", vol.MaxValue)
		}
		if vol.Range != 4.0 {
			t.Errorf("Expected range 4.0, got %.2f", vol.Range)
		}

		t.Logf("Stats: mean=%.2f, stddev=%.2f, cv=%.4f", vol.MeanValue, vol.StdDev, vol.CV)
	})
}

func TestAdapt(t *testing.T) {
	cfg := config.AdaptiveDownsamplingConfig{
		VolatilityThreshold: 0.5,
		MinWindow:           time.Minute,
		MaxWindow:           time.Hour,
		HighVolatilityLevel: config.LevelMinute,
		LowVolatilityLevel:  config.Level15Minutes,
		AdaptationRate:      0.5,
	}
	engine := NewAdaptiveEngine(cfg)

	baseTime := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)

	t.Run("adapt to high volatility", func(t *testing.T) {
		engine.Reset()

		samples := make([]prometheus.Sample, 20)
		for i := 0; i < 20; i++ {
			val := 10.0
			if i%2 == 0 {
				val = 100.0
			}
			samples[i] = prometheus.Sample{
				Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
				Value:     val,
			}
		}

		result := engine.Adapt(samples, 0)

		if !result.Adaptation {
			t.Errorf("Expected adaptation to occur")
		}
		if result.Window.Level != config.LevelMinute {
			t.Errorf("Expected high volatility level %s, got %s",
				config.LevelMinute, result.Window.Level)
		}

		t.Logf("Adapted: %v, level: %s, volatility: %.4f",
			result.Adaptation, result.Window.Level, result.Volatility)
	})

	t.Run("adapt to low volatility", func(t *testing.T) {
		engine.Reset()

		samples := make([]prometheus.Sample, 20)
		for i := 0; i < 20; i++ {
			samples[i] = prometheus.Sample{
				Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
				Value:     10.0,
			}
		}

		result := engine.Adapt(samples, 0)

		if result.Window.Level != config.Level15Minutes {
			t.Errorf("Expected low volatility level %s, got %s",
				config.Level15Minutes, result.Window.Level)
		}

		t.Logf("Level: %s, volatility: %.4f", result.Window.Level, result.Volatility)
	})
}

func TestErrorAnalysis(t *testing.T) {
	cfg := config.ErrorAnalysisConfig{
		Enabled:          true,
		CalculateMAE:     true,
		CalculateRMSE:    true,
		CalculateMAPE:    true,
		CalculateSMAPE:   true,
		CalculateCorrelation: true,
		AlertThreshold:   0.1,
	}
	analyzer := NewErrorAnalyzer(cfg)

	baseTime := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)

	t.Run("perfect accuracy", func(t *testing.T) {
		original := make([]prometheus.Sample, 10)
		downsampled := make([]DownsampledPoint, 2)

		for i := 0; i < 10; i++ {
			original[i] = prometheus.Sample{
				Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
				Value:     float64(i + 1),
			}
		}

		downsampled[0] = DownsampledPoint{
			Timestamp: baseTime,
			Value:     3.0,
			Level:     config.LevelMinute,
		}
		downsampled[1] = DownsampledPoint{
			Timestamp: baseTime.Add(time.Minute),
			Value:     8.0,
			Level:     config.LevelMinute,
		}

		metrics := analyzer.Analyze(original, downsampled)

		t.Logf("MAE: %.4f, RMSE: %.4f, MAPE: %.2f%%, Correlation: %.4f",
			metrics.MAE, metrics.RMSE, metrics.MAPE, metrics.Correlation)

		if metrics.TotalSamples == 0 {
			t.Errorf("Expected samples to be compared")
		}
	})

	t.Run("exceeds threshold", func(t *testing.T) {
		original := []prometheus.Sample{
			{Timestamp: baseTime, Value: 100},
			{Timestamp: baseTime.Add(30 * time.Second), Value: 200},
		}

		downsampled := []DownsampledPoint{
			{Timestamp: baseTime, Value: 50},
		}

		metrics := analyzer.Analyze(original, downsampled)

		if !analyzer.IsErrorExceedsThreshold(metrics) {
			t.Errorf("Expected error to exceed threshold")
		}

		t.Logf("Error: MAPE=%.2f%%, exceeds threshold: %v",
			metrics.MAPE, analyzer.IsErrorExceedsThreshold(metrics))
	})

	t.Run("quality report", func(t *testing.T) {
		original := make([]prometheus.Sample, 10)
		downsampled := make([]DownsampledPoint, 2)

		for i := 0; i < 10; i++ {
			original[i] = prometheus.Sample{
				Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
				Value:     float64(i + 1),
			}
		}

		downsampled[0] = DownsampledPoint{
			Timestamp: baseTime,
			Value:     3.0,
			Level:     config.LevelMinute,
		}
		downsampled[1] = DownsampledPoint{
			Timestamp: baseTime.Add(time.Minute),
			Value:     8.0,
			Level:     config.LevelMinute,
		}

		metrics := analyzer.Analyze(original, downsampled)
		report := analyzer.GenerateErrorReport(metrics)

		t.Logf("Quality: %v", report["quality"])
		t.Logf("Exceeds threshold: %v", report["exceeds_threshold"])
	})
}

func TestRecommendation(t *testing.T) {
	cfg := config.StrategyRecommendationConfig{
		Enabled:              true,
		AnalyzePeriod:        24 * time.Hour,
		MinSamples:           10,
		TargetErrorThreshold: 0.1,
		StorageCostWeight:    0.6,
		AccuracyWeight:       0.4,
	}
	engine := NewRecommendationEngine(cfg)

	baseTime := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)

	t.Run("low volatility metric", func(t *testing.T) {
		samples := make([]prometheus.Sample, 50)
		for i := 0; i < 50; i++ {
			samples[i] = prometheus.Sample{
				Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
				Value:     10.0 + float64(i)*0.01,
			}
		}

		series := prometheus.TimeSeries{
			Labels: map[string]string{
				"__name__": "test_low_vol",
				"instance": "server1",
			},
			Samples: samples,
		}

		features := engine.AnalyzeMetrics(series)
		rec := engine.GetBestRecommendation(features)

		if rec == nil {
			t.Fatalf("Expected recommendation")
		}

		t.Logf("Metric: %s", rec.MetricName)
		t.Logf("Volatility: %.4f", rec.Volatility)
		t.Logf("Recommended levels: %v", rec.RecommendedLevels)
		t.Logf("Estimated error: %.2f%%", rec.EstimatedError)
		t.Logf("Estimated saving: %.2f%%", rec.EstimatedSaving)
		t.Logf("Score: %.2f", rec.Score)
		t.Logf("Reasoning: %s", rec.Reasoning)

		if rec.EstimatedSaving < 70 {
			t.Errorf("Expected high saving for low volatility, got %.2f%%", rec.EstimatedSaving)
		}
	})

	t.Run("high volatility metric", func(t *testing.T) {
		samples := make([]prometheus.Sample, 50)
		for i := 0; i < 50; i++ {
			val := 10.0
			if i%2 == 0 {
				val = 100.0
			}
			samples[i] = prometheus.Sample{
				Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
				Value:     val,
			}
		}

		series := prometheus.TimeSeries{
			Labels: map[string]string{
				"__name__": "test_high_vol",
				"instance": "server1",
			},
			Samples: samples,
		}

		features := engine.AnalyzeMetrics(series)
		rec := engine.GetBestRecommendation(features)

		if rec == nil {
			t.Fatalf("Expected recommendation")
		}

		t.Logf("Metric: %s", rec.MetricName)
		t.Logf("Volatility: %.4f", rec.Volatility)
		t.Logf("Adaptive enabled: %v", rec.AdaptiveEnabled)
		t.Logf("Preserve peaks: %v", rec.PreservePeaks)
		t.Logf("Preserve outliers: %v", rec.PreserveOutliers)

		if !rec.AdaptiveEnabled {
			t.Errorf("Expected adaptive to be enabled for high volatility")
		}
		if !rec.PreservePeaks {
			t.Errorf("Expected peak preservation for high volatility")
		}
	})

	t.Run("generate config from recommendation", func(t *testing.T) {
		samples := make([]prometheus.Sample, 50)
		for i := 0; i < 50; i++ {
			samples[i] = prometheus.Sample{
				Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
				Value:     float64(i),
			}
		}

		series := prometheus.TimeSeries{
			Labels: map[string]string{
				"__name__": "test_auto_config",
			},
			Samples: samples,
		}

		features := engine.AnalyzeMetrics(series)
		rec := engine.GetBestRecommendation(features)

		if rec == nil {
			t.Fatalf("Expected recommendation")
		}

		rule := engine.GenerateConfigFromRecommendation(rec)

		if rule.Name == "" {
			t.Errorf("Expected rule name to be set")
		}
		if rule.Match == "" {
			t.Errorf("Expected rule match to be set")
		}
		if len(rule.Aggregations) == 0 {
			t.Errorf("Expected aggregations to be set")
		}
		if len(rule.DownsamplingLevels) == 0 {
			t.Errorf("Expected downsampling levels to be set")
		}

		t.Logf("Generated rule: %s", rule.Name)
		t.Logf("Match: %s", rule.Match)
		t.Logf("Aggregations: %v", rule.Aggregations)
		t.Logf("Levels: %v", rule.DownsamplingLevels)
		t.Logf("Adaptive enabled: %v", rule.AdaptiveDownsampling.Enabled)
		t.Logf("Error analysis enabled: %v", rule.ErrorAnalysis.Enabled)
	})
}

func TestDetrend(t *testing.T) {
	baseTime := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)

	samples := make([]prometheus.Sample, 20)
	for i := 0; i < 20; i++ {
		samples[i] = prometheus.Sample{
			Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
			Value:     float64(i) * 2.0,
		}
	}

	detrended := Detrend(samples)

	if len(detrended) != len(samples) {
		t.Errorf("Expected same length after detrend")
	}

	var sum float64
	for _, s := range detrended {
		sum += s.Value
	}
	mean := sum / float64(len(detrended))

	if math.Abs(mean) > 1.0 {
		t.Errorf("Expected detrended mean close to 0, got %.4f", mean)
	}

	t.Logf("Original trend: y = 2x, detrended mean: %.4f", mean)
}

func TestPercentile(t *testing.T) {
	values := []float64{1, 2, 3, 4, 5, 6, 7, 8, 9, 10}

	p50 := percentile(values, 50)
	if p50 != 5.5 {
		t.Errorf("Expected p50 = 5.5, got %.2f", p50)
	}

	p90 := percentile(values, 90)
	t.Logf("p90: %.2f", p90)
	if p90 < 9 || p90 > 10 {
		t.Errorf("Expected p90 between 9 and 10, got %.2f", p90)
	}
}

func TestLevelDuration(t *testing.T) {
	cfg := config.AdaptiveDownsamplingConfig{}
	engine := NewAdaptiveEngine(cfg)

	testCases := []struct {
		level    config.DownsamplingLevel
		expected time.Duration
	}{
		{config.LevelMinute, time.Minute},
		{config.Level5Minutes, 5 * time.Minute},
		{config.Level15Minutes, 15 * time.Minute},
		{config.LevelHour, time.Hour},
		{config.Level6Hours, 6 * time.Hour},
		{config.LevelDay, 24 * time.Hour},
	}

	for _, tc := range testCases {
		t.Run(string(tc.level), func(t *testing.T) {
			d := engine.GetLevelDuration(tc.level)
			if d != tc.expected {
				t.Errorf("Expected %v, got %v", tc.expected, d)
			}
		})
	}
}
