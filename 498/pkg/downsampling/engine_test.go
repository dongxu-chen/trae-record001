package downsampling

import (
	"testing"
	"time"

	"github.com/prometheus/downsampler/pkg/config"
	"github.com/prometheus/downsampler/pkg/prometheus"
)

func TestAvgAggregator(t *testing.T) {
	agg := &AvgAggregator{}
	values := []float64{1, 2, 3, 4, 5}
	result := agg.Aggregate(values)
	if result != 3.0 {
		t.Errorf("Expected 3.0, got %f", result)
	}

	result = agg.Aggregate([]float64{})
	if result != result {
		t.Errorf("Expected NaN for empty input")
	}
}

func TestMaxAggregator(t *testing.T) {
	agg := &MaxAggregator{}
	values := []float64{1, 5, 3, 9, 2}
	result := agg.Aggregate(values)
	if result != 9.0 {
		t.Errorf("Expected 9.0, got %f", result)
	}
}

func TestMinAggregator(t *testing.T) {
	agg := &MinAggregator{}
	values := []float64{1, 5, 3, 9, 2}
	result := agg.Aggregate(values)
	if result != 1.0 {
		t.Errorf("Expected 1.0, got %f", result)
	}
}

func TestSumAggregator(t *testing.T) {
	agg := &SumAggregator{}
	values := []float64{1, 2, 3, 4, 5}
	result := agg.Aggregate(values)
	if result != 15.0 {
		t.Errorf("Expected 15.0, got %f", result)
	}
}

func TestCountAggregator(t *testing.T) {
	agg := &CountAggregator{}
	values := []float64{1, 2, 3, 4, 5}
	result := agg.Aggregate(values)
	if result != 5.0 {
		t.Errorf("Expected 5.0, got %f", result)
	}
}

func TestPercentileAggregator(t *testing.T) {
	agg := &PercentileAggregator{Percentile: 50}
	values := []float64{1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
	result := agg.Aggregate(values)
	if result != 5.5 {
		t.Errorf("Expected 5.5 for p50, got %f", result)
	}

	agg99 := &PercentileAggregator{Percentile: 99}
	result = agg99.Aggregate(values)
	if result < 9.9 || result > 10.0 {
		t.Errorf("Expected ~10.0 for p99, got %f", result)
	}
}

func TestNewAggregator(t *testing.T) {
	tests := []struct {
		fn      config.AggregationFunction
		wantErr bool
	}{
		{config.AggAvg, false},
		{config.AggMax, false},
		{config.AggMin, false},
		{config.AggSum, false},
		{config.AggCount, false},
		{config.AggP50, false},
		{config.AggP90, false},
		{config.AggP95, false},
		{config.AggP99, false},
		{config.AggregationFunction("invalid"), true},
	}

	for _, tt := range tests {
		_, err := NewAggregator(tt.fn)
		if (err != nil) != tt.wantErr {
			t.Errorf("NewAggregator(%s) error = %v, wantErr %v", tt.fn, err, tt.wantErr)
		}
	}
}

func TestDownsample(t *testing.T) {
	engine := NewEngine("test")

	baseTime := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	samples := make([]prometheus.Sample, 120)
	for i := 0; i < 120; i++ {
		samples[i] = prometheus.Sample{
			Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
			Value:     float64(i),
		}
	}

	series := prometheus.TimeSeries{
		Labels: map[string]string{
			"__name__": "test_metric",
			"instance": "server1",
			"job":      "test",
		},
		Samples: samples,
	}

	rule := config.MetricRule{
		Name:               "test_rule",
		Match:              `{__name__="test_metric"}`,
		Aggregations:       []config.AggregationFunction{config.AggAvg, config.AggMax},
		DownsamplingLevels: []config.DownsamplingLevel{config.LevelMinute},
		PreserveLabels:     []string{"instance"},
		AlignToBoundary:    true,
	}

	start := baseTime
	end := baseTime.Add(30 * time.Minute)

	points, err := engine.Downsample(series, rule, start, end)
	if err != nil {
		t.Fatalf("Downsample failed: %v", err)
	}

	var aggregatedPoints []DownsampledPoint
	for _, p := range points {
		if p.PointType == PointTypeAggregated {
			aggregatedPoints = append(aggregatedPoints, p)
		}
	}

	expectedBuckets := 30
	expectedPoints := expectedBuckets * 2
	if len(aggregatedPoints) != expectedPoints {
		t.Errorf("Expected %d aggregated points, got %d", expectedPoints, len(aggregatedPoints))
	}

	hasAvg := false
	hasMax := false
	for _, p := range aggregatedPoints {
		if p.Aggregation == config.AggAvg {
			hasAvg = true
		}
		if p.Aggregation == config.AggMax {
			hasMax = true
		}
		if p.Labels["instance"] != "server1" {
			t.Errorf("Expected instance label to be preserved")
		}
		if _, exists := p.Labels["job"]; exists {
			t.Errorf("Expected job label to be dropped")
		}
		if p.Labels["ds_level"] != string(config.LevelMinute) {
			t.Errorf("Expected ds_level label to be set")
		}
		if p.Labels["ds_type"] != string(PointTypeAggregated) {
			t.Errorf("Expected ds_type label to be 'aggregated'")
		}
	}

	if !hasAvg || !hasMax {
		t.Errorf("Expected both avg and max aggregations")
	}
}

func TestAlignToBoundary(t *testing.T) {
	engine := NewEngine("test")

	testCases := []struct {
		name     string
		input    time.Time
		window   time.Duration
		expected time.Time
	}{
		{
			name:     "minute boundary",
			input:    time.Date(2024, 1, 1, 10, 5, 30, 0, time.UTC),
			window:   time.Minute,
			expected: time.Date(2024, 1, 1, 10, 5, 0, 0, time.UTC),
		},
		{
			name:     "hour boundary",
			input:    time.Date(2024, 1, 1, 10, 5, 30, 0, time.UTC),
			window:   time.Hour,
			expected: time.Date(2024, 1, 1, 10, 0, 0, 0, time.UTC),
		},
		{
			name:     "5min boundary",
			input:    time.Date(2024, 1, 1, 10, 7, 30, 0, time.UTC),
			window:   5 * time.Minute,
			expected: time.Date(2024, 1, 1, 10, 5, 0, 0, time.UTC),
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			result := engine.alignToBoundary(tc.input, tc.window)
			if !result.Equal(tc.expected) {
				t.Errorf("Expected %v, got %v", tc.expected, result)
			}
		})
	}
}

func TestDetectPeaks(t *testing.T) {
	engine := NewEngine("test")

	baseTime := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	samples := make([]prometheus.Sample, 30)
	for i := 0; i < 30; i++ {
		val := 10.0
		if i == 10 {
			val = 100.0
		}
		if i == 20 {
			val = 150.0
		}
		samples[i] = prometheus.Sample{
			Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
			Value:     val,
		}
	}

	series := prometheus.TimeSeries{
		Labels: map[string]string{
			"__name__": "test_metric",
			"instance": "server1",
		},
		Samples: samples,
	}

	rule := config.MetricRule{
		Name:               "test_rule",
		Match:              `{__name__="test_metric"}`,
		Aggregations:       []config.AggregationFunction{config.AggAvg},
		DownsamplingLevels: []config.DownsamplingLevel{config.LevelMinute},
		PreserveLabels:     []string{"instance"},
		AlignToBoundary:    true,
		PreservePeaks: config.PeakDetectionConfig{
			Enabled:        true,
			ZScoreThreshold: 2.0,
			Percentile:     95.0,
		},
	}

	start := baseTime
	end := baseTime.Add(10 * time.Minute)

	points, err := engine.Downsample(series, rule, start, end)
	if err != nil {
		t.Fatalf("Downsample failed: %v", err)
	}

	peakCount := 0
	for _, p := range points {
		if p.PointType == PointTypePeak {
			peakCount++
		}
	}

	t.Logf("Found %d peak points", peakCount)
}

func TestDetectOutliers(t *testing.T) {
	engine := NewEngine("test")

	baseTime := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	samples := make([]prometheus.Sample, 20)
	for i := 0; i < 20; i++ {
		val := 10.0 + float64(i)*0.1
		if i == 5 {
			val = 1000.0
		}
		if i == 15 {
			val = -100.0
		}
		samples[i] = prometheus.Sample{
			Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
			Value:     val,
		}
	}

	series := prometheus.TimeSeries{
		Labels: map[string]string{
			"__name__": "test_metric",
			"instance": "server1",
		},
		Samples: samples,
	}

	rule := config.MetricRule{
		Name:               "test_rule",
		Match:              `{__name__="test_metric"}`,
		Aggregations:       []config.AggregationFunction{config.AggAvg},
		DownsamplingLevels: []config.DownsamplingLevel{config.LevelMinute},
		PreserveLabels:     []string{"instance"},
		AlignToBoundary:    true,
		PreserveOutliers: config.OutlierDetectionConfig{
			Enabled:       true,
			IQRMultiplier: 1.5,
			PreserveCount: 5,
		},
	}

	start := baseTime
	end := baseTime.Add(10 * time.Minute)

	points, err := engine.Downsample(series, rule, start, end)
	if err != nil {
		t.Fatalf("Downsample failed: %v", err)
	}

	outlierCount := 0
	for _, p := range points {
		if p.PointType == PointTypeOutlier {
			outlierCount++
			t.Logf("Outlier detected: value=%f, raw_time=%v", p.Value, p.RawTimestamp)
		}
	}

	t.Logf("Found %d outlier points", outlierCount)
}

func TestPointTypes(t *testing.T) {
	if PointTypeAggregated != "aggregated" {
		t.Errorf("Expected PointTypeAggregated to be 'aggregated'")
	}
	if PointTypePeak != "peak" {
		t.Errorf("Expected PointTypePeak to be 'peak'")
	}
	if PointTypeOutlier != "outlier" {
		t.Errorf("Expected PointTypeOutlier to be 'outlier'")
	}
}

func TestProcessLabels(t *testing.T) {
	engine := NewEngine("test")

	labels := map[string]string{
		"__name__": "test",
		"a":        "1",
		"b":        "2",
		"c":        "3",
		"d":        "4",
	}

	rule := config.MetricRule{
		PreserveLabels: []string{"a", "b"},
	}

	result := engine.processLabels(labels, rule)
	if len(result) != 2 {
		t.Errorf("Expected 2 labels, got %d", len(result))
	}
	if result["a"] != "1" || result["b"] != "2" {
		t.Errorf("Expected labels a and b to be preserved")
	}

	rule2 := config.MetricRule{
		DropLabels: []string{"c", "d"},
	}

	result2 := engine.processLabels(labels, rule2)
	if len(result2) != 2 {
		t.Errorf("Expected 2 labels, got %d", len(result2))
	}
	if result2["a"] != "1" || result2["b"] != "2" {
		t.Errorf("Expected labels a and b to be kept")
	}
}

func TestGenerateMetricName(t *testing.T) {
	engine := NewEngine("ds")

	name := engine.GenerateMetricName("http_requests", config.AvgP99, config.LevelHour)
	expected := "ds:http_requests:p99:1h"
	if name != expected {
		t.Errorf("Expected %s, got %s", expected, name)
	}
}

func TestProcessQueryResult(t *testing.T) {
	engine := NewEngine("test")

	baseTime := time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC)
	samples := make([]prometheus.Sample, 60)
	for i := 0; i < 60; i++ {
		samples[i] = prometheus.Sample{
			Timestamp: baseTime.Add(time.Duration(i) * 15 * time.Second),
			Value:     float64(i),
		}
	}

	queryResult := &prometheus.QueryResult{
		Series: []prometheus.TimeSeries{
			{
				Labels:  map[string]string{"__name__": "test", "instance": "s1"},
				Samples: samples,
			},
		},
	}

	rule := config.MetricRule{
		Name:               "test",
		Match:              `{__name__="test"}`,
		Aggregations:       []config.AggregationFunction{config.AggAvg},
		DownsamplingLevels: []config.DownsamplingLevel{config.LevelMinute},
	}

	start := baseTime
	end := baseTime.Add(15 * time.Minute)

	result := engine.ProcessQueryResult(queryResult, rule, start, end)
	if result.Error != nil {
		t.Fatalf("ProcessQueryResult failed: %v", result.Error)
	}

	if result.InputCount != 60 {
		t.Errorf("Expected InputCount 60, got %d", result.InputCount)
	}

	if result.OutputCount != 15 {
		t.Errorf("Expected OutputCount 15, got %d", result.OutputCount)
	}
}

func TestDownsamplingLevelDuration(t *testing.T) {
	tests := []struct {
		level   config.DownsamplingLevel
		want    time.Duration
		wantErr bool
	}{
		{config.LevelRaw, 0, false},
		{config.LevelMinute, time.Minute, false},
		{config.Level5Minutes, 5 * time.Minute, false},
		{config.Level15Minutes, 15 * time.Minute, false},
		{config.LevelHour, time.Hour, false},
		{config.Level6Hours, 6 * time.Hour, false},
		{config.LevelDay, 24 * time.Hour, false},
		{config.DownsamplingLevel("invalid"), 0, true},
	}

	for _, tt := range tests {
		got, err := tt.level.Duration()
		if (err != nil) != tt.wantErr {
			t.Errorf("Level %s: error = %v, wantErr %v", tt.level, err, tt.wantErr)
			continue
		}
		if got != tt.want {
			t.Errorf("Level %s: got %v, want %v", tt.level, got, tt.want)
		}
	}
}
