package analysis

import (
	"context"
	"db-bench/internal/storage"
	"encoding/json"
	"fmt"
	"math"
	"sort"
	"time"
)

type ComparisonSummary struct {
	RunIDs      []string
	Metrics     []ComparisonMetric
	Trend       string
	Improvement float64
}

type ComparisonMetric struct {
	Name    string
	Unit    string
	Values  map[string]float64
	BestRun string
	BestVal float64
}

type ReplayOptions struct {
	OutputFormat string
	StartTime    time.Time
	EndTime      time.Time
	SampleRate   int
}

type AnalysisResult struct {
	RunID            string
	PeakQPS          float64
	PeakQPSAt        time.Time
	AvgQPS           float64
	MinP99           float64
	MaxP99           float64
	AvgP99           float64
	StabilityScore   float64
	ErrorRateTrend   string
	LatencyTrend     string
	InflectionPoint  float64
	InflectionLatency float64
	SaturationPoint  bool
}

func AnalyzeRun(ctx context.Context, store *storage.Storage, runID string) (*AnalysisResult, error) {
	run, err := store.GetRun(ctx, runID)
	if err != nil {
		return nil, fmt.Errorf("failed to get run: %w", err)
	}

	points, err := store.GetTimeSeries(ctx, runID)
	if err != nil {
		return nil, fmt.Errorf("failed to get timeseries: %w", err)
	}

	if len(points) == 0 {
		return nil, fmt.Errorf("no timeseries data for run %s", runID)
	}

	result := &AnalysisResult{
		RunID: runID,
	}

	var totalQPS, totalP99 float64
	var qpsValues, p99Values []float64
	result.MaxP99 = math.Inf(-1)
	result.MinP99 = math.Inf(1)
	result.PeakQPS = math.Inf(-1)

	for _, p := range points {
		totalQPS += p.QPS
		totalP99 += p.P99
		qpsValues = append(qpsValues, p.QPS)
		p99Values = append(p99Values, p.P99)

		if p.QPS > result.PeakQPS {
			result.PeakQPS = p.QPS
			result.PeakQPSAt = p.Timestamp
		}
		if p.P99 > result.MaxP99 {
			result.MaxP99 = p.P99
		}
		if p.P99 < result.MinP99 {
			result.MinP99 = p.P99
		}
	}

	result.AvgQPS = totalQPS / float64(len(points))
	result.AvgP99 = totalP99 / float64(len(points))

	qpsStd := calculateStdDev(qpsValues, result.AvgQPS)
	if result.AvgQPS > 0 {
		result.StabilityScore = 100.0 - (qpsStd/result.AvgQPS)*100.0
	} else {
		result.StabilityScore = 0
	}

	result.ErrorRateTrend = calculateTrend(points, func(p storage.TimeSeriesPoint) float64 { return p.ErrorRate })
	result.LatencyTrend = calculateTrend(points, func(p storage.TimeSeriesPoint) float64 { return p.P99 })

	detectInflection(points, result)

	return result, nil
}

func CompareRuns(ctx context.Context, store *storage.Storage, runIDs []string) (*ComparisonSummary, error) {
	results := make(map[string]*AnalysisResult)
	for _, runID := range runIDs {
		r, err := AnalyzeRun(ctx, store, runID)
		if err != nil {
			return nil, err
		}
		results[runID] = r
	}

	summary := &ComparisonSummary{
		RunIDs: runIDs,
	}

	metricDefs := []struct {
		name     string
		unit     string
		getValue func(*AnalysisResult) float64
		higher   bool
	}{
		{"Peak QPS", "ops/s", func(r *AnalysisResult) float64 { return r.PeakQPS }, true},
		{"Avg QPS", "ops/s", func(r *AnalysisResult) float64 { return r.AvgQPS }, true},
		{"Avg P99", "ms", func(r *AnalysisResult) float64 { return r.AvgP99 }, false},
		{"Min P99", "ms", func(r *AnalysisResult) float64 { return r.MinP99 }, false},
		{"Max P99", "ms", func(r *AnalysisResult) float64 { return r.MaxP99 }, false},
		{"Stability", "%", func(r *AnalysisResult) float64 { return r.StabilityScore }, true},
		{"Inflection QPS", "ops/s", func(r *AnalysisResult) float64 { return r.InflectionPoint }, true},
	}

	var bestQPS, baselineQPS float64
	var bestRun string

	for i, md := range metricDefs {
		metric := ComparisonMetric{
			Name:   md.name,
			Unit:   md.unit,
			Values: make(map[string]float64),
		}

		var bestVal float64
		if md.higher {
			bestVal = math.Inf(-1)
		} else {
			bestVal = math.Inf(1)
		}

		for _, runID := range runIDs {
			val := md.getValue(results[runID])
			metric.Values[runID] = val

			if md.higher && val > bestVal {
				bestVal = val
				bestRun = runID
			} else if !md.higher && val < bestVal {
				bestVal = val
				bestRun = runID
			}
		}

		metric.BestRun = bestRun
		metric.BestVal = bestVal
		summary.Metrics = append(summary.Metrics, metric)

		if i == 0 {
			bestQPS = bestVal
			baselineQPS = metric.Values[runIDs[0]]
		}
	}

	if baselineQPS > 0 {
		summary.Improvement = (bestQPS - baselineQPS) / baselineQPS * 100.0
		if summary.Improvement > 5 {
			summary.Trend = "improved"
		} else if summary.Improvement < -5 {
			summary.Trend = "degraded"
		} else {
			summary.Trend = "stable"
		}
	} else {
		summary.Trend = "unknown"
	}

	return summary, nil
}

func GenerateReport(summary *ComparisonSummary) string {
	report := "=== Benchmark Comparison Report ===\n\n"

	for _, runID := range summary.RunIDs {
		report += fmt.Sprintf("Run: %s\n", runID)
	}
	report += "\n"

	for _, metric := range summary.Metrics {
		report += fmt.Sprintf("%s (%s):\n", metric.Name, metric.Unit)
		for _, runID := range summary.RunIDs {
			val := metric.Values[runID]
			marker := ""
			if runID == metric.BestRun {
				marker = " ← BEST"
			}
			report += fmt.Sprintf("  %s: %.2f%s\n", runID, val, marker)
		}
		report += "\n"
	}

	if summary.Trend != "" {
		report += fmt.Sprintf("Overall Trend: %s (%.1f%% change)\n", summary.Trend, summary.Improvement)
	}

	return report
}

func GenerateJSONReport(summary *ComparisonSummary) (string, error) {
	data, err := MarshalJSON(summary)
	if err != nil {
		return "", err
	}
	return string(data), nil
}

func MarshalJSON(v interface{}) ([]byte, error) {
	return json.MarshalIndent(v, "", "  ")
}

func ReplayData(ctx context.Context, store *storage.Storage, runID string, opts ReplayOptions) ([]storage.TimeSeriesPoint, error) {
	points, err := store.GetTimeSeries(ctx, runID)
	if err != nil {
		return nil, err
	}

	if !opts.StartTime.IsZero() || !opts.EndTime.IsZero() {
		var filtered []storage.TimeSeriesPoint
		for _, p := range points {
			if (!opts.StartTime.IsZero() && p.Timestamp.Before(opts.StartTime)) ||
				(!opts.EndTime.IsZero() && p.Timestamp.After(opts.EndTime)) {
				continue
			}
			filtered = append(filtered, p)
		}
		points = filtered
	}

	if opts.SampleRate > 1 && len(points) > opts.SampleRate {
		var sampled []storage.TimeSeriesPoint
		step := len(points) / opts.SampleRate
		for i := 0; i < len(points); i += step {
			sampled = append(sampled, points[i])
		}
		points = sampled
	}

	return points, nil
}

func ExportCSV(ctx context.Context, store *storage.Storage, runID string) (string, error) {
	points, err := store.GetTimeSeries(ctx, runID)
	if err != nil {
		return "", err
	}

	csv := "timestamp,elapsed_sec,concurrency,qps,tps,error_rate,p50,p99,p999,total_ops,instant_qps\n"
	for _, p := range points {
		csv += fmt.Sprintf("%s,%.2f,%d,%.2f,%.2f,%.4f,%.2f,%.2f,%.2f,%d,%.2f\n",
			p.Timestamp.Format(time.RFC3339), p.ElapsedSec, p.Concurrency,
			p.QPS, p.TPS, p.ErrorRate, p.P50, p.P99, p.P999, p.TotalOps, p.InstantQPS)
	}

	return csv, nil
}

func calculateStdDev(values []float64, mean float64) float64 {
	if len(values) == 0 {
		return 0
	}
	var sum float64
	for _, v := range values {
		sum += (v - mean) * (v - mean)
	}
	return math.Sqrt(sum / float64(len(values)))
}

func calculateTrend(points []storage.TimeSeriesPoint, getter func(storage.TimeSeriesPoint) float64) string {
	if len(points) < 5 {
		return "insufficient_data"
	}

	firstHalf := points[:len(points)/2]
	secondHalf := points[len(points)/2:]

	var firstAvg, secondAvg float64
	for _, p := range firstHalf {
		firstAvg += getter(p)
	}
	for _, p := range secondHalf {
		secondAvg += getter(p)
	}
	firstAvg /= float64(len(firstHalf))
	secondAvg /= float64(len(secondHalf))

	change := (secondAvg - firstAvg) / firstAvg * 100

	if math.Abs(change) < 2 {
		return "stable"
	} else if change > 10 {
		return "increasing_significantly"
	} else if change > 0 {
		return "increasing_slightly"
	} else if change < -10 {
		return "decreasing_significantly"
	} else {
		return "decreasing_slightly"
	}
}

func detectInflection(points []storage.TimeSeriesPoint, result *AnalysisResult) {
	if len(points) < 10 {
		return
	}

	window := 5
	var qpsGradient []float64

	for i := window; i < len(points)-window; i++ {
		prevAvg := avgQPS(points[i-window : i])
		nextAvg := avgQPS(points[i : i+window])
		gradient := nextAvg - prevAvg
		qpsGradient = append(qpsGradient, gradient)
	}

	if len(qpsGradient) < 3 {
		return
	}

	for i := 1; i < len(qpsGradient)-1; i++ {
		if qpsGradient[i-1] > 0 && qpsGradient[i] <= 0 && qpsGradient[i+1] <= 0 {
			inflectionIdx := i + window
			if inflectionIdx < len(points) {
				result.InflectionPoint = points[inflectionIdx].QPS
				result.InflectionLatency = points[inflectionIdx].P99
				result.SaturationPoint = true
				break
			}
		}
	}
}

func avgQPS(points []storage.TimeSeriesPoint) float64 {
	if len(points) == 0 {
		return 0
	}
	var sum float64
	for _, p := range points {
		sum += p.QPS
	}
	return sum / float64(len(points))
}

func ListRunsTable(runs []storage.BenchmarkRun) string {
	if len(runs) == 0 {
		return "No benchmark runs found."
	}

	table := fmt.Sprintf("%-20s  %-10s  %-8s  %-8s  %-12s  %-8s  %-8s  %-8s  %s\n",
		"Run ID", "DB", "Status", "Duration", "QPS", "P50", "P99", "P999", "Start Time")
	table += "-----------------------------------------------------------------------------------------------------------\n"

	sort.Slice(runs, func(i, j int) bool {
		return runs[i].StartTime.After(runs[j].StartTime)
	})

	for _, r := range runs {
		duration := "N/A"
		if r.DurationSeconds > 0 {
			duration = fmt.Sprintf("%.0fs", r.DurationSeconds)
		}
		qps := "N/A"
		if r.FinalQPS > 0 {
			qps = fmt.Sprintf("%.0f", r.FinalQPS)
		}
		p50 := "N/A"
		if r.FinalP50 > 0 {
			p50 = fmt.Sprintf("%.1fms", r.FinalP50)
		}
		p99 := "N/A"
		if r.FinalP99 > 0 {
			p99 = fmt.Sprintf("%.1fms", r.FinalP99)
		}
		p999 := "N/A"
		if r.FinalP999 > 0 {
			p999 = fmt.Sprintf("%.1fms", r.FinalP999)
		}

		table += fmt.Sprintf("%-20s  %-10s  %-8s  %-8s  %-12s  %-8s  %-8s  %-8s  %s\n",
			shortenID(r.RunID), r.DatabaseType, r.Status, duration, qps, p50, p99, p999,
			r.StartTime.Format("2006-01-02 15:04:05"))
	}

	return table
}

func shortenID(id string) string {
	if len(id) > 20 {
		return id[:17] + "..."
	}
	return id
}
