package analysis

import (
	"math"
	"time"

	"github.com/prometheus/downsampler/pkg/config"
	"github.com/prometheus/downsampler/pkg/prometheus"
)

type ErrorAnalyzer struct {
	cfg config.ErrorAnalysisConfig
}

func NewErrorAnalyzer(cfg config.ErrorAnalysisConfig) *ErrorAnalyzer {
	return &ErrorAnalyzer{cfg: cfg}
}

func (ea *ErrorAnalyzer) Analyze(original []prometheus.Sample, downsampled []DownsampledPoint) ErrorMetrics {
	if len(original) == 0 || len(downsampled) == 0 {
		return ErrorMetrics{}
	}

	comparisons := ea.CompareSamples(original, downsampled)
	if len(comparisons) == 0 {
		return ErrorMetrics{}
	}

	var mae, rmse, mape, smape, corr float64
	var maxErr, minErr, meanErr float64
	var errVariance float64

	errors := make([]float64, len(comparisons))
	absErrors := make([]float64, len(comparisons))
	pctErrors := make([]float64, len(comparisons))

	var sumRaw, sumDown, sumRawSq, sumDownSq, sumCross float64

	for i, c := range comparisons {
		errors[i] = c.Error
		absErrors[i] = math.Abs(c.Error)
		pctErrors[i] = c.PercentageError

		sumRaw += c.RawValue
		sumDown += c.DownsampledValue
		sumRawSq += c.RawValue * c.RawValue
		sumDownSq += c.DownsampledValue * c.DownsampledValue
		sumCross += c.RawValue * c.DownsampledValue
	}

	n := float64(len(comparisons))

	if ea.cfg.CalculateMAE {
		sumAbs := 0.0
		for _, e := range absErrors {
			sumAbs += e
		}
		mae = sumAbs / n
	}

	if ea.cfg.CalculateRMSE {
		sumSq := 0.0
		for _, e := range errors {
			sumSq += e * e
		}
		rmse = math.Sqrt(sumSq / n)
	}

	if ea.cfg.CalculateMAPE {
		sumPct := 0.0
		validCount := 0.0
		for _, p := range pctErrors {
			if !math.IsInf(p, 0) && !math.IsNaN(p) {
				sumPct += p
				validCount++
			}
		}
		if validCount > 0 {
			mape = sumPct / validCount
		}
	}

	if ea.cfg.CalculateSMAPE {
		sumSmape := 0.0
		for _, c := range comparisons {
			denom := math.Abs(c.RawValue) + math.Abs(c.DownsampledValue)
			if denom > 0 {
				sumSmape += math.Abs(c.Error) / denom * 200.0
			}
		}
		smape = sumSmape / n
	}

	if ea.cfg.CalculateCorrelation {
		numerator := n*sumCross - sumRaw*sumDown
		denominator := math.Sqrt((n*sumRawSq - sumRaw*sumRaw) * (n*sumDownSq - sumDown*sumDown))
		if denominator != 0 {
			corr = numerator / denominator
		}
	}

	maxErr = absErrors[0]
	minErr = absErrors[0]
	sumErr := 0.0
	for _, e := range absErrors {
		if e > maxErr {
			maxErr = e
		}
		if e < minErr {
			minErr = e
		}
		sumErr += e
	}
	meanErr = sumErr / n

	sqDiff := 0.0
	for _, e := range absErrors {
		diff := e - meanErr
		sqDiff += diff * diff
	}
	errVariance = sqDiff / n
	stdDevErr := math.Sqrt(errVariance)

	return ErrorMetrics{
		MAE:          mae,
		RMSE:         rmse,
		MAPE:         mape,
		SMAPE:        smape,
		Correlation:  corr,
		MaxError:     maxErr,
		MinError:     minErr,
		MeanError:    meanErr,
		StdDevError:  stdDevErr,
		TotalSamples: len(comparisons),
		Timestamp:    time.Now(),
	}
}

func (ea *ErrorAnalyzer) CompareSamples(original []prometheus.Sample, downsampled []DownsampledPoint) []SampleComparison {
	if len(original) == 0 || len(downsampled) == 0 {
		return nil
	}

	var comparisons []SampleComparison
	downIdx := 0

	for _, orig := range original {
		for downIdx < len(downsampled)-1 &&
			orig.Timestamp.After(downsampled[downIdx+1].Timestamp) {
			downIdx++
		}

		if downIdx < len(downsampled) {
			ds := downsampled[downIdx]
			err := orig.Value - ds.Value

			var pctErr float64
			if orig.Value != 0 {
				pctErr = math.Abs(err/orig.Value) * 100.0
			} else {
				pctErr = math.Inf(1)
			}

			comparisons = append(comparisons, SampleComparison{
				RawValue:         orig.Value,
				DownsampledValue: ds.Value,
				Timestamp:        orig.Timestamp,
				Error:            err,
				PercentageError:  pctErr,
			})
		}
	}

	return comparisons
}

func (ea *ErrorAnalyzer) IsErrorExceedsThreshold(metrics ErrorMetrics) bool {
	if ea.cfg.AlertThreshold <= 0 {
		return false
	}

	if ea.cfg.CalculateMAPE && metrics.MAPE > ea.cfg.AlertThreshold*100 {
		return true
	}
	if ea.cfg.CalculateRMSE && metrics.RMSE > ea.cfg.AlertThreshold {
		return true
	}
	if ea.cfg.CalculateMAE && metrics.MAE > ea.cfg.AlertThreshold {
		return true
	}

	return false
}

func (ea *ErrorAnalyzer) AggregateErrors(metrics []ErrorMetrics) ErrorMetrics {
	if len(metrics) == 0 {
		return ErrorMetrics{}
	}

	var totalMAE, totalRMSE, totalMAPE, totalSMAPE, totalCorr float64
	var totalMaxErr, totalMinErr, totalMeanErr, totalStdDev float64
	var totalSamples int

	validMAE := 0
	validRMSE := 0
	validMAPE := 0
	validSMAPE := 0
	validCorr := 0

	for _, m := range metrics {
		if ea.cfg.CalculateMAE {
			totalMAE += m.MAE
			validMAE++
		}
		if ea.cfg.CalculateRMSE {
			totalRMSE += m.RMSE * m.RMSE
			validRMSE++
		}
		if ea.cfg.CalculateMAPE && !math.IsNaN(m.MAPE) && !math.IsInf(m.MAPE, 0) {
			totalMAPE += m.MAPE
			validMAPE++
		}
		if ea.cfg.CalculateSMAPE {
			totalSMAPE += m.SMAPE
			validSMAPE++
		}
		if ea.cfg.CalculateCorrelation && !math.IsNaN(m.Correlation) {
			totalCorr += m.Correlation
			validCorr++
		}

		if m.MaxError > totalMaxErr {
			totalMaxErr = m.MaxError
		}
		if totalMinErr == 0 || m.MinError < totalMinErr {
			totalMinErr = m.MinError
		}
		totalMeanErr += m.MeanError
		totalStdDev += m.StdDevError
		totalSamples += m.TotalSamples
	}

	n := float64(len(metrics))
	if validMAE > 0 {
		totalMAE /= float64(validMAE)
	}
	if validRMSE > 0 {
		totalRMSE = math.Sqrt(totalRMSE / float64(validRMSE))
	}
	if validMAPE > 0 {
		totalMAPE /= float64(validMAPE)
	}
	if validSMAPE > 0 {
		totalSMAPE /= float64(validSMAPE)
	}
	if validCorr > 0 {
		totalCorr /= float64(validCorr)
	}
	totalMeanErr /= n
	totalStdDev /= n

	return ErrorMetrics{
		MAE:          totalMAE,
		RMSE:         totalRMSE,
		MAPE:         totalMAPE,
		SMAPE:        totalSMAPE,
		Correlation:  totalCorr,
		MaxError:     totalMaxErr,
		MinError:     totalMinErr,
		MeanError:    totalMeanErr,
		StdDevError:  totalStdDev,
		TotalSamples: totalSamples,
		Timestamp:    time.Now(),
	}
}

func (ea *ErrorAnalyzer) GenerateErrorReport(metrics ErrorMetrics) map[string]interface{} {
	report := make(map[string]interface{})

	if ea.cfg.CalculateMAE {
		report["mae"] = metrics.MAE
	}
	if ea.cfg.CalculateRMSE {
		report["rmse"] = metrics.RMSE
	}
	if ea.cfg.CalculateMAPE {
		report["mape_percent"] = metrics.MAPE
	}
	if ea.cfg.CalculateSMAPE {
		report["smape_percent"] = metrics.SMAPE
	}
	if ea.cfg.CalculateCorrelation {
		report["correlation"] = metrics.Correlation
	}

	report["max_error"] = metrics.MaxError
	report["min_error"] = metrics.MinError
	report["mean_error"] = metrics.MeanError
	report["stddev_error"] = metrics.StdDevError
	report["total_samples"] = metrics.TotalSamples
	report["timestamp"] = metrics.Timestamp
	report["exceeds_threshold"] = ea.IsErrorExceedsThreshold(metrics)

	var quality string
	switch {
	case ea.cfg.CalculateMAPE && metrics.MAPE < 1:
		quality = "excellent"
	case ea.cfg.CalculateMAPE && metrics.MAPE < 5:
		quality = "good"
	case ea.cfg.CalculateMAPE && metrics.MAPE < 10:
		quality = "fair"
	case ea.cfg.CalculateMAPE && metrics.MAPE < 20:
		quality = "poor"
	default:
		quality = "unknown"
	}
	report["quality"] = quality

	return report
}
