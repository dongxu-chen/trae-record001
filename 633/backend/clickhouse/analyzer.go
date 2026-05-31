package clickhouse

import (
	"context"
	"fmt"
	"math"
	"regexp"
	"strings"
)

type QueryPrediction struct {
	EstimatedCPUTimeMs   float64 `json:"estimated_cpu_time_ms"`
	EstimatedIOMB        float64 `json:"estimated_io_mb"`
	EstimatedNetworkMB   float64 `json:"estimated_network_mb"`
	EstimatedDurationMs  float64 `json:"estimated_duration_ms"`
	ConcurrencyImpact    float64 `json:"concurrency_impact"`
	ResourcePressure     string  `json:"resource_pressure"`
}

type QueryComplexity struct {
	EstimatedRows   int64   `json:"estimated_rows"`
	EstimatedMemory int64   `json:"estimated_memory"`
	EstimatedCost   float64 `json:"estimated_cost"`
	ComplexityScore float64 `json:"complexity_score"`
	RiskLevel       string  `json:"risk_level"`
	HasJoin         bool    `json:"has_join"`
	HasGroupBy      bool    `json:"has_group_by"`
	HasOrderBy      bool    `json:"has_order_by"`
	HasAggregation  bool    `json:"has_aggregation"`
	TableCount      int     `json:"table_count"`
	PlanStages      []PlanStage `json:"plan_stages,omitempty"`
	CostBreakdown   map[string]float64 `json:"cost_breakdown,omitempty"`
	Prediction      *QueryPrediction `json:"prediction,omitempty"`
}

type QueryAnalyzer struct {
	chClient *Client
}

func NewQueryAnalyzer(chClient *Client) *QueryAnalyzer {
	return &QueryAnalyzer{
		chClient: chClient,
	}
}

func (qa *QueryAnalyzer) AnalyzeQuery(ctx context.Context, query string) *QueryComplexity {
	complexity := &QueryComplexity{
		CostBreakdown: make(map[string]float64),
	}

	upperQuery := strings.ToUpper(query)
	complexity.HasJoin = strings.Contains(upperQuery, "JOIN")
	complexity.HasGroupBy = strings.Contains(upperQuery, "GROUP BY")
	complexity.HasOrderBy = strings.Contains(upperQuery, "ORDER BY")
	complexity.HasAggregation = containsAggregationFunctions(upperQuery)
	complexity.TableCount = countTables(query)

	plan, err := qa.chClient.GetExplainPlan(ctx, query)
	if err == nil && plan != nil {
		complexity.EstimatedRows = plan.EstimatedRows
		complexity.EstimatedMemory = plan.EstimatedMemory
		complexity.EstimatedCost = plan.EstimatedCost
		complexity.PlanStages = plan.Stages

		complexity.calculateCostBreakdown(plan)
	} else {
		complexity.EstimatedRows = qa.fallbackEstimateRows(query, complexity)
		complexity.EstimatedMemory = complexity.EstimatedRows * 128
		complexity.EstimatedCost = float64(complexity.EstimatedRows) * 0.001
	}

	complexity.ComplexityScore = complexity.calculateComplexityScore()
	complexity.RiskLevel = getRiskLevel(complexity.ComplexityScore)
	complexity.Prediction = complexity.calculatePrediction()

	return complexity
}

func (qc *QueryComplexity) calculateCostBreakdown(plan *ExplainPlan) {
	totalCost := plan.EstimatedCost
	if totalCost <= 0 {
		totalCost = 1
	}

	rowCost := float64(plan.EstimatedRows) * 0.001
	memoryCost := float64(plan.EstimatedMemory) / 1024.0 / 1024.0 * 0.1

	qc.CostBreakdown["row_scan"] = rowCost / totalCost * 100
	qc.CostBreakdown["memory"] = memoryCost / totalCost * 100

	for _, stage := range plan.Stages {
		switch stage.Name {
		case "Join":
			qc.CostBreakdown["join"] = qc.CostBreakdown["join"] + 20
		case "Aggregating":
			qc.CostBreakdown["aggregation"] = qc.CostBreakdown["aggregation"] + 15
		case "Sorting":
			qc.CostBreakdown["sorting"] = qc.CostBreakdown["sorting"] + 10
		}
	}
}

func max64(a, b int64) int64 {
	if a > b {
		return a
	}
	return b
}

func (qc *QueryComplexity) calculatePrediction() *QueryPrediction {
	pred := &QueryPrediction{}

	rowsFactor := float64(max64(qc.EstimatedRows, 1))
	memoryGB := float64(qc.EstimatedMemory) / (1024.0 * 1024.0 * 1024.0)

	perRowCycles := 10.0
	if qc.HasJoin {
		perRowCycles *= 3.0
	}
	if qc.HasGroupBy {
		perRowCycles *= 2.5
	}
	if qc.HasOrderBy {
		perRowCycles *= 2.0
	}
	if qc.HasAggregation {
		perRowCycles *= 1.5
	}

	cpuCycles := rowsFactor * perRowCycles
	pred.EstimatedCPUTimeMs = cpuCycles / 3000000.0

	ioPerRow := 64.0
	if qc.HasJoin {
		ioPerRow *= 2.0
	}
	pred.EstimatedIOMB = (rowsFactor * ioPerRow) / (1024.0 * 1024.0)

	networkPerRow := 32.0
	if qc.HasGroupBy {
		networkPerRow *= 0.5
	}
	pred.EstimatedNetworkMB = (rowsFactor * networkPerRow) / (1024.0 * 1024.0)

	baseDurationMs := rowsFactor * 0.001
	cpuFactor := pred.EstimatedCPUTimeMs * 0.3
	ioFactor := pred.EstimatedIOMB * 5.0
	pred.EstimatedDurationMs = baseDurationMs + cpuFactor + ioFactor
	if pred.EstimatedDurationMs < 1.0 {
		pred.EstimatedDurationMs = 1.0
	}

	pred.ConcurrencyImpact = qc.ComplexityScore / 10.0
	if pred.ConcurrencyImpact > 1.0 {
		pred.ConcurrencyImpact = 1.0
	}

	switch {
	case qc.ComplexityScore >= 15.0:
		pred.ResourcePressure = "EXTREME"
	case qc.ComplexityScore >= 10.0:
		pred.ResourcePressure = "HIGH"
	case qc.ComplexityScore >= 5.0:
		pred.ResourcePressure = "MEDIUM"
	default:
		pred.ResourcePressure = "LOW"
	}

	return pred
}

func (qc *QueryComplexity) calculateComplexityScore() float64 {
	score := 0.0

	rowsScore := math.Log10(float64(max64(qc.EstimatedRows, 1))+1) * 2
	score += rowsScore

	memoryGB := float64(qc.EstimatedMemory) / (1024.0 * 1024.0 * 1024.0)
	memoryScore := memoryGB * 5
	score += memoryScore

	costScore := math.Log10(qc.EstimatedCost+1) * 1.5
	score += costScore

	if qc.HasJoin {
		score += 2.0 * float64(qc.TableCount-1)
	}

	if qc.HasGroupBy {
		score += 1.5
	}

	if qc.HasOrderBy {
		score += 1.0
	}

	if qc.HasAggregation {
		score += 1.0
	}

	return math.Round(score*10) / 10
}

func (qa *QueryAnalyzer) fallbackEstimateRows(query string, complexity *QueryComplexity) int64 {
	baseRows := int64(1000000)

	hasLimit, limitCount := extractLimit(query)
	if hasLimit {
		baseRows = int64(limitCount)
	}

	if complexity.HasJoin {
		baseRows *= max64(int64(complexity.TableCount), 1)
	}

	if complexity.HasGroupBy {
		baseRows *= 2
	}

	if complexity.HasAggregation {
		baseRows *= 2
	}

	if complexity.HasOrderBy && !hasLimit {
		baseRows *= 3
	}

	return baseRows
}

func containsAggregationFunctions(query string) bool {
	aggFuncs := []string{"COUNT(", "SUM(", "AVG(", "MIN(", "MAX(", "GROUP_ARRAY", "UNIQ("}
	for _, fn := range aggFuncs {
		if strings.Contains(query, fn) {
			return true
		}
	}
	return false
}

func countTables(query string) int {
	tableRegex := regexp.MustCompile(`(?i)FROM\s+(\w+)|JOIN\s+(\w+)`)
	matches := tableRegex.FindAllStringSubmatch(query, -1)
	
	tableSet := make(map[string]bool)
	for _, match := range matches {
		for i := 1; i < len(match); i++ {
			if match[i] != "" {
				tableSet[strings.ToLower(match[i])] = true
			}
		}
	}
	
	count := len(tableSet)
	if count == 0 {
		return 1
	}
	return count
}

func extractLimit(query string) (bool, int) {
	limitRegex := regexp.MustCompile(`(?i)LIMIT\s+(\d+)`)
	match := limitRegex.FindStringSubmatch(query)
	if len(match) > 1 {
		count := 0
		fmt.Sscanf(match[1], "%d", &count)
		return true, count
	}
	return false, 0
}

func getRiskLevel(score float64) string {
	switch {
	case score >= 15.0:
		return "CRITICAL"
	case score >= 10.0:
		return "HIGH"
	case score >= 5.0:
		return "MEDIUM"
	default:
		return "LOW"
	}
}
