package analysis

import (
	"time"

	"github.com/prometheus/downsampler/pkg/config"
	"github.com/prometheus/downsampler/pkg/prometheus"
)

type PointType string

const (
	PointTypeRaw        PointType = "raw"
	PointTypeAggregated PointType = "aggregated"
	PointTypePeak       PointType = "peak"
	PointTypeOutlier    PointType = "outlier"
)

type DownsampledPoint struct {
	Timestamp     time.Time
	Value         float64
	RawTimestamp  *time.Time
	Labels        map[string]string
	Aggregation   config.AggregationFunction
	Level         config.DownsamplingLevel
	PointType     PointType
	WindowSize    time.Duration
}

type ErrorMetrics struct {
	MAE          float64
	RMSE         float64
	MAPE         float64
	SMAPE        float64
	Correlation  float64
	MaxError     float64
	MinError     float64
	MeanError    float64
	StdDevError  float64
	TotalSamples int
	Timestamp    time.Time
}

type VolatilityMetrics struct {
	Volatility       float64
	Trend            float64
	Seasonality      float64
	Noise            float64
	CV               float64
	MaxValue         float64
	MinValue         float64
	MeanValue        float64
	StdDev           float64
	Range            float64
	ZeroCrossings    int
	Percentile95     float64
	Percentile5      float64
	Skewness         float64
	Kurtosis         float64
}

type Recommendation struct {
	MetricName           string
	Labels               map[string]string
	RecommendedLevels    []config.DownsamplingLevel
	RecommendedAggs      []config.AggregationFunction
	EstimatedError       float64
	EstimatedSaving      float64
	Score                float64
	Reasoning            string
	AnalysisPeriod       time.Duration
	SampleCount          int
	Volatility           float64
	AdaptiveEnabled      bool
	AdaptiveHighLevel    config.DownsamplingLevel
	AdaptiveLowLevel     config.DownsamplingLevel
	PreservePeaks        bool
	PreserveOutliers     bool
}

type WindowInfo struct {
	Level      config.DownsamplingLevel
	Duration   time.Duration
	IsAdaptive bool
}

type AdaptiveResult struct {
	Window          WindowInfo
	Volatility      float64
	Adaptation      bool
	PreviousWindow  WindowInfo
}

type SampleComparison struct {
	RawValue       float64
	DownsampledValue float64
	Timestamp      time.Time
	Error          float64
	PercentageError float64
}

type AnalysisResult struct {
	OriginalSeries   prometheus.TimeSeries
	Downsampled      []DownsampledPoint
	ErrorMetrics     ErrorMetrics
	Volatility       VolatilityMetrics
	Recommendations  []Recommendation
	Comparisons      []SampleComparison
}

type AnalysisConfig struct {
	Adaptive    config.AdaptiveDownsamplingConfig
	Error       config.ErrorAnalysisConfig
	Strategy    config.StrategyRecommendationConfig
}

type MetricsCache struct {
	Volatility VolatilityMetrics
	Timestamp  time.Time
	TTL        time.Duration
}
