package predictor

import (
	"fmt"
	"math"
	"sort"
	"strings"
	"sync"
	"time"

	"slow-query-killer/internal/analyzer"
	"slow-query-killer/internal/db"
)

type QueryTrend struct {
	QueryHash      string
	QueryType      string
	QuerySample    string
	Timeseries     []TimePoint
	TrendSlope     float64
	TrendDirection string
	RiskLevel      string
	PredictedTime  time.Duration
	KilledCount    int
	LastKilled     time.Time
}

type TimePoint struct {
	Timestamp     time.Time
	ExecutionTime time.Duration
}

type PredictionResult struct {
	QueryHash     string
	QuerySample   string
	RiskLevel     string
	CurrentTime   time.Duration
	PredictedTime time.Duration
	WillBeKilled  bool
	TimeToKill    time.Duration
	Confidence    float64
}

type Predictor struct {
	queryHistory   map[string][]TimePoint
	queryKills     map[string]int
	lastKillTimes  map[string]time.Time
	querySamples   map[string]string
	queryTypes     map[string]string
	historyLock    sync.RWMutex
	maxHistorySize int
	predictWindow  time.Duration
	killThreshold  time.Duration
}

func NewPredictor(killThreshold time.Duration) *Predictor {
	return &Predictor{
		queryHistory:   make(map[string][]TimePoint),
		queryKills:     make(map[string]int),
		lastKillTimes:  make(map[string]time.Time),
		querySamples:   make(map[string]string),
		queryTypes:     make(map[string]string),
		maxHistorySize: 100,
		predictWindow:  5 * time.Minute,
		killThreshold:  killThreshold,
	}
}

func (p *Predictor) RecordQuery(query *db.SlowQuery) {
	normalized := analyzer.NormalizeQuery(query.Query)
	queryHash := analyzer.HashQuery(normalized)

	p.historyLock.Lock()
	defer p.historyLock.Unlock()

	p.queryHistory[queryHash] = append(p.queryHistory[queryHash], TimePoint{
		Timestamp:     time.Now(),
		ExecutionTime: query.ExecutionTime,
	})

	if len(p.queryHistory[queryHash]) > p.maxHistorySize {
		p.queryHistory[queryHash] = p.queryHistory[queryHash][1:]
	}

	if _, exists := p.querySamples[queryHash]; !exists {
		p.querySamples[queryHash] = truncateQuery(query.Query, 200)
		p.queryTypes[queryHash] = detectQueryType(query.Query)
	}
}

func (p *Predictor) RecordKill(queryHash string) {
	p.historyLock.Lock()
	defer p.historyLock.Unlock()

	p.queryKills[queryHash]++
	p.lastKillTimes[queryHash] = time.Now()
}

func (p *Predictor) Predict(queryHash string) *PredictionResult {
	p.historyLock.RLock()
	defer p.historyLock.RUnlock()

	history, exists := p.queryHistory[queryHash]
	if !exists || len(history) < 3 {
		return nil
	}

	slope := calculateSlope(history)
	currentTime := history[len(history)-1].ExecutionTime

	predictedSeconds := currentTime.Seconds() + slope*60
	predictedTime := time.Duration(predictedSeconds * float64(time.Second))

	willBeKilled := predictedTime >= p.killThreshold

	var timeToKill time.Duration
	if willBeKilled && slope > 0 {
		timeToThreshold := p.killThreshold.Seconds() - currentTime.Seconds()
		if timeToThreshold > 0 {
			minutesToKill := timeToThreshold / slope
			timeToKill = time.Duration(minutesToKill * float64(time.Minute))
		}
	}

	confidence := calculateConfidence(history, slope)

	riskLevel := calculateRiskLevel(slope, predictedTime, p.killThreshold)

	return &PredictionResult{
		QueryHash:     queryHash,
		QuerySample:   p.querySamples[queryHash],
		RiskLevel:     riskLevel,
		CurrentTime:   currentTime,
		PredictedTime: predictedTime,
		WillBeKilled:  willBeKilled,
		TimeToKill:    timeToKill,
		Confidence:    confidence,
	}
}

func (p *Predictor) GetAllTrends() []QueryTrend {
	p.historyLock.RLock()
	defer p.historyLock.RUnlock()

	trends := make([]QueryTrend, 0, len(p.queryHistory))

	for hash, history := range p.queryHistory {
		if len(history) < 3 {
			continue
		}

		slope := calculateSlope(history)
		trendDir := "stable"
		if slope > 0.1 {
			trendDir = "increasing"
		} else if slope < -0.1 {
			trendDir = "decreasing"
		}

		currentTime := history[len(history)-1].ExecutionTime
		predictedSeconds := currentTime.Seconds() + slope*60

		trends = append(trends, QueryTrend{
			QueryHash:      hash,
			QueryType:      p.queryTypes[hash],
			QuerySample:    p.querySamples[hash],
			Timeseries:     history,
			TrendSlope:     slope,
			TrendDirection: trendDir,
			RiskLevel:      calculateRiskLevel(slope, time.Duration(predictedSeconds*float64(time.Second)), p.killThreshold),
			PredictedTime:  time.Duration(predictedSeconds * float64(time.Second)),
			KilledCount:    p.queryKills[hash],
			LastKilled:     p.lastKillTimes[hash],
		})
	}

	sort.Slice(trends, func(i, j int) bool {
		return trends[i].KilledCount > trends[j].KilledCount
	})

	return trends
}

func (p *Predictor) GetHighRiskQueries(threshold float64) []PredictionResult {
	p.historyLock.RLock()
	defer p.historyLock.RUnlock()

	results := make([]PredictionResult, 0)

	for hash := range p.queryHistory {
		pred := p.Predict(hash)
		if pred != nil && pred.Confidence >= threshold {
			results = append(results, *pred)
		}
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].RiskLevel > results[j].RiskLevel
	})

	return results
}

func calculateSlope(history []TimePoint) float64 {
	n := len(history)
	if n < 2 {
		return 0
	}

	var sumX, sumY, sumXY, sumX2 float64

	for i, point := range history {
		x := float64(i)
		y := point.ExecutionTime.Seconds()
		sumX += x
		sumY += y
		sumXY += x * y
		sumX2 += x * x
	}

	slope := (float64(n)*sumXY - sumX*sumY) / (float64(n)*sumX2 - sumX*sumX)
	return slope
}

func calculateConfidence(history []TimePoint, slope float64) float64 {
	if len(history) < 3 {
		return 0
	}

	var variance float64
	mean := 0.0
	for _, p := range history {
		mean += p.ExecutionTime.Seconds()
	}
	mean /= float64(len(history))

	for _, p := range history {
		variance += math.Pow(p.ExecutionTime.Seconds()-mean, 2)
	}
	variance /= float64(len(history))

	stdDev := math.Sqrt(variance)
	cv := stdDev / mean

	confidence := 1.0 - cv
	if confidence < 0 {
		confidence = 0
	}

	slopeWeight := math.Abs(slope) * 0.1
	if slopeWeight > 0.5 {
		slopeWeight = 0.5
	}
	confidence = confidence*0.7 + slopeWeight

	return confidence
}

func calculateRiskLevel(slope float64, predictedTime time.Duration, killThreshold time.Duration) string {
	ratio := predictedTime.Seconds() / killThreshold.Seconds()

	if slope > 0.5 && ratio >= 0.9 {
		return "CRITICAL"
	} else if slope > 0.2 && ratio >= 0.7 {
		return "HIGH"
	} else if slope > 0 && ratio >= 0.5 {
		return "MEDIUM"
	} else if ratio >= 0.3 {
		return "LOW"
	}
	return "NORMAL"
}

func detectQueryType(query string) string {
	upper := strings.ToUpper(strings.TrimSpace(query))
	switch {
	case strings.HasPrefix(upper, "SELECT"):
		return "SELECT"
	case strings.HasPrefix(upper, "INSERT"):
		return "INSERT"
	case strings.HasPrefix(upper, "UPDATE"):
		return "UPDATE"
	case strings.HasPrefix(upper, "DELETE"):
		return "DELETE"
	default:
		return "OTHER"
	}
}

func truncateQuery(query string, maxLen int) string {
	if len(query) <= maxLen {
		return query
	}
	return query[:maxLen] + "..."
}

func (p *Predictor) GeneratePredictionReport() string {
	trends := p.GetAllTrends()
	if len(trends) == 0 {
		return "No query trends available for prediction."
	}

	var report strings.Builder
	report.WriteString("\n=== Slow Query Trend Prediction Report ===\n")
	report.WriteString(fmt.Sprintf("Total queries tracked: %d\n\n", len(trends)))

	highRiskCount := 0
	criticalCount := 0
	for _, t := range trends {
		if t.RiskLevel == "CRITICAL" {
			criticalCount++
		} else if t.RiskLevel == "HIGH" {
			highRiskCount++
		}
	}

	report.WriteString(fmt.Sprintf("Critical risk queries: %d\n", criticalCount))
	report.WriteString(fmt.Sprintf("High risk queries: %d\n\n", highRiskCount))

	report.WriteString("Top 10 Most Problematic Queries:\n")
	report.WriteString(strings.Repeat("-", 100) + "\n")

	limit := 10
	if len(trends) < limit {
		limit = len(trends)
	}

	for i := 0; i < limit; i++ {
		t := trends[i]
		report.WriteString(fmt.Sprintf("\n%d. Risk: %s | Type: %s\n", i+1, t.RiskLevel, t.QueryType))
		report.WriteString(fmt.Sprintf("   Trend: %s (slope: %.2f)\n", t.TrendDirection, t.TrendSlope))
		report.WriteString(fmt.Sprintf("   Predicted next: %v | Killed: %d times\n", t.PredictedTime, t.KilledCount))
		if !t.LastKilled.IsZero() {
			report.WriteString(fmt.Sprintf("   Last killed: %v ago\n", time.Since(t.LastKilled).Round(time.Second)))
		}
		report.WriteString(fmt.Sprintf("   Sample: %s\n", t.QuerySample))
	}

	return report.String()
}
