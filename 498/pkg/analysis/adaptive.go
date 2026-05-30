package analysis

import (
	"math"
	"time"

	"github.com/prometheus/downsampler/pkg/config"
	"github.com/prometheus/downsampler/pkg/prometheus"
)

type AdaptiveEngine struct {
	cfg          config.AdaptiveDownsamplingConfig
	currentLevel config.DownsamplingLevel
	cache        *MetricsCache
	levelDurations map[config.DownsamplingLevel]time.Duration
}

func NewAdaptiveEngine(cfg config.AdaptiveDownsamplingConfig) *AdaptiveEngine {
	levelDurations := map[config.DownsamplingLevel]time.Duration{
		config.LevelMinute:     time.Minute,
		config.Level5Minutes:   5 * time.Minute,
		config.Level15Minutes:  15 * time.Minute,
		config.LevelHour:       time.Hour,
		config.Level6Hours:     6 * time.Hour,
		config.LevelDay:        24 * time.Hour,
	}

	return &AdaptiveEngine{
		cfg:            cfg,
		currentLevel:   cfg.LowVolatilityLevel,
		cache:          &MetricsCache{TTL: 5 * time.Minute},
		levelDurations: levelDurations,
	}
}

func (a *AdaptiveEngine) CalculateVolatility(samples []prometheus.Sample) VolatilityMetrics {
	if len(samples) == 0 {
		return VolatilityMetrics{}
	}

	values := make([]float64, len(samples))
	for i, s := range samples {
		values[i] = s.Value
	}

	n := float64(len(values))

	mean := 0.0
	for _, v := range values {
		mean += v
	}
	mean /= n

	variance := 0.0
	for _, v := range values {
		diff := v - mean
		variance += diff * diff
	}
	variance /= n
	stdDev := math.Sqrt(variance)

	cv := 0.0
	if mean != 0 {
		cv = stdDev / math.Abs(mean)
	}

	diffCount := 0
	diffSum := 0.0
	for i := 1; i < len(values); i++ {
		diff := math.Abs(values[i] - values[i-1])
		diffSum += diff
		diffCount++
	}

	volatility := 0.0
	if diffCount > 0 && stdDev > 0 {
		volatility = (diffSum / float64(diffCount)) / stdDev
	}

	trend := 0.0
	if len(values) > 1 {
		trend = (values[len(values)-1] - values[0]) / float64(len(values)-1)
	}

	maxVal := values[0]
	minVal := values[0]
	for _, v := range values {
		if v > maxVal {
			maxVal = v
		}
		if v < minVal {
			minVal = v
		}
	}

	zeroCrossings := 0
	for i := 1; i < len(values); i++ {
		if (values[i-1] >= 0 && values[i] < 0) || (values[i-1] < 0 && values[i] >= 0) {
			zeroCrossings++
		}
	}

	sortedValues := make([]float64, len(values))
	copy(sortedValues, values)
	for i := range sortedValues {
		for j := i + 1; j < len(sortedValues); j++ {
			if sortedValues[i] > sortedValues[j] {
				sortedValues[i], sortedValues[j] = sortedValues[j], sortedValues[i]
			}
		}
	}

	p5 := percentile(sortedValues, 5)
	p95 := percentile(sortedValues, 95)

	skewness := 0.0
	if stdDev > 0 {
		for _, v := range values {
			diff := (v - mean) / stdDev
			skewness += diff * diff * diff
		}
		skewness /= n
	}

	kurtosis := 0.0
	if stdDev > 0 {
		for _, v := range values {
			diff := (v - mean) / stdDev
			kurtosis += diff * diff * diff * diff
		}
		kurtosis = kurtosis/n - 3
	}

	return VolatilityMetrics{
		Volatility:    volatility,
		Trend:         trend,
		CV:            cv,
		MaxValue:      maxVal,
		MinValue:      minVal,
		MeanValue:     mean,
		StdDev:        stdDev,
		Range:         maxVal - minVal,
		ZeroCrossings: zeroCrossings,
		Percentile95:  p95,
		Percentile5:   p5,
		Skewness:      skewness,
		Kurtosis:      kurtosis,
	}
}

func (a *AdaptiveEngine) Adapt(samples []prometheus.Sample, currentWindow time.Duration) AdaptiveResult {
	vol := a.CalculateVolatility(samples)

	previousLevel := a.currentLevel
	previousDuration := a.levelDurations[previousLevel]

	var newLevel config.DownsamplingLevel
	if vol.Volatility > a.cfg.VolatilityThreshold {
		newLevel = a.cfg.HighVolatilityLevel
	} else {
		newLevel = a.cfg.LowVolatilityLevel
	}

	if a.cfg.AdaptationRate > 0 && a.cfg.AdaptationRate < 1 {
		prevDur := a.levelDurations[a.currentLevel]
		newDur := a.levelDurations[newLevel]
		smoothedDur := time.Duration(float64(prevDur)*(1-a.cfg.AdaptationRate) + float64(newDur)*a.cfg.AdaptationRate)

		newLevel = a.findClosestLevel(smoothedDur)
	}

	newDuration := a.levelDurations[newLevel]
	if newDuration < a.cfg.MinWindow {
		newDuration = a.cfg.MinWindow
		newLevel = a.findClosestLevel(newDuration)
	}
	if newDuration > a.cfg.MaxWindow {
		newDuration = a.cfg.MaxWindow
		newLevel = a.findClosestLevel(newDuration)
	}

	a.currentLevel = newLevel

	adapted := newLevel != previousLevel

	a.cache.Volatility = vol
	a.cache.Timestamp = time.Now()

	return AdaptiveResult{
		Window: WindowInfo{
			Level:      newLevel,
			Duration:   newDuration,
			IsAdaptive: true,
		},
		Volatility: vol.Volatility,
		Adaptation: adapted,
		PreviousWindow: WindowInfo{
			Level:      previousLevel,
			Duration:   previousDuration,
			IsAdaptive: true,
		},
	}
}

func (a *AdaptiveEngine) GetAdaptiveWindows(samples []prometheus.Sample) []WindowInfo {
	if len(samples) == 0 {
		return nil
	}

	windowSize := a.cfg.VolatilityWindowSize
	var windows []WindowInfo

	for i := 0; i < len(samples); i += windowSize {
		end := i + windowSize
		if end > len(samples) {
			end = len(samples)
		}

		windowSamples := samples[i:end]
		result := a.Adapt(windowSamples, 0)
		windows = append(windows, result.Window)
	}

	return windows
}

func (a *AdaptiveEngine) Reset() {
	a.currentLevel = a.cfg.LowVolatilityLevel
}

func (a *AdaptiveEngine) GetCurrentLevel() config.DownsamplingLevel {
	return a.currentLevel
}

func (a *AdaptiveEngine) GetLevelDuration(level config.DownsamplingLevel) time.Duration {
	if d, ok := a.levelDurations[level]; ok {
		return d
	}
	return time.Minute
}

func (a *AdaptiveEngine) findClosestLevel(duration time.Duration) config.DownsamplingLevel {
	var closest config.DownsamplingLevel
	minDiff := time.Duration(math.MaxInt64)

	for level, d := range a.levelDurations {
		diff := d - duration
		if diff < 0 {
			diff = -diff
		}
		if diff < minDiff {
			minDiff = diff
			closest = level
		}
	}

	return closest
}

func percentile(sortedValues []float64, p float64) float64 {
	if len(sortedValues) == 0 {
		return 0
	}
	idx := (p / 100.0) * float64(len(sortedValues)-1)
	lower := int(math.Floor(idx))
	upper := int(math.Ceil(idx))
	if lower == upper {
		return sortedValues[lower]
	}
	weight := idx - float64(lower)
	return sortedValues[lower]*(1-weight) + sortedValues[upper]*weight
}

func Detrend(samples []prometheus.Sample) []prometheus.Sample {
	if len(samples) < 2 {
		return samples
	}

	n := len(samples)
	var sumX, sumY, sumXY, sumX2 float64

	for i := 0; i < n; i++ {
		x := float64(i)
		y := samples[i].Value
		sumX += x
		sumY += y
		sumXY += x * y
		sumX2 += x * x
	}

	slope := (float64(n)*sumXY - sumX*sumY) / (float64(n)*sumX2 - sumX*sumX)
	intercept := (sumY - slope*sumX) / float64(n)

	detrended := make([]prometheus.Sample, n)
	for i := 0; i < n; i++ {
		trend := intercept + slope*float64(i)
		detrended[i] = prometheus.Sample{
			Timestamp: samples[i].Timestamp,
			Value:     samples[i].Value - trend,
		}
	}

	return detrended
}
