package services

import (
	"fmt"
	"math"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/prometheus/prometheus/promql/parser"
)

type Metric struct {
	Name   string            `json:"name"`
	Labels map[string]string `json:"labels"`
	Value  float64           `json:"value"`
	Time   time.Time         `json:"time"`
}

type TimeSeriesPoint struct {
	Timestamp time.Time `json:"timestamp"`
	Value     float64   `json:"value"`
}

type TimeSeriesMetric struct {
	Name   string            `json:"name"`
	Labels map[string]string `json:"labels"`
	Points []TimeSeriesPoint `json:"points"`
}

type ValidateResult struct {
	Valid    bool                   `json:"valid"`
	ExprType string                 `json:"expr_type"`
	ASTInfo  map[string]interface{} `json:"ast_info,omitempty"`
	Error    string                 `json:"error,omitempty"`
	Message  string                 `json:"message"`
}

type SimulateResult struct {
	Firing            bool                   `json:"firing"`
	FiringFor         string                 `json:"firing_for,omitempty"`
	MatchedTimeSeries []MatchedTimeSeries    `json:"matched_time_series,omitempty"`
	MatchedLabels     []map[string]string    `json:"matched_labels,omitempty"`
	Values            []float64              `json:"values,omitempty"`
	Timeline          []TimelineEvent        `json:"timeline,omitempty"`
	Message           string                 `json:"message"`
	DurationVerified  bool                   `json:"duration_verified"`
	RequiredDuration  string                 `json:"required_duration,omitempty"`
	ActualDuration    string                 `json:"actual_duration,omitempty"`
}

type MatchedTimeSeries struct {
	Name         string             `json:"name"`
	Labels       map[string]string  `json:"labels"`
	CurrentValue float64            `json:"current_value"`
	Firing       bool               `json:"firing"`
	FiringStart  *time.Time         `json:"firing_start,omitempty"`
	FiringFor    string             `json:"firing_for,omitempty"`
	PointCount   int                `json:"point_count"`
	Values       []float64          `json:"values,omitempty"`
	Timestamps   []time.Time        `json:"timestamps,omitempty"`
}

type TimelineEvent struct {
	Timestamp time.Time `json:"timestamp"`
	EventType string    `json:"event_type"` // "start_firing", "stop_firing", "duration_met"
	Message   string    `json:"message"`
}

type selector struct {
	name    string
	labels  map[string]string
	matches map[string]*regexp.Regexp
}

func ValidatePromQL(expr string) (string, error) {
	ast, err := parser.ParseExpr(expr)
	if err != nil {
		return "", err
	}
	return ast.Type().String(), nil
}

func ValidatePromQLDetailed(expr string) *ValidateResult {
	ast, err := parser.ParseExpr(expr)
	if err != nil {
		return &ValidateResult{
			Valid:   false,
			Error:   err.Error(),
			Message: "PromQL syntax is invalid",
		}
	}

	astInfo := make(map[string]interface{})
	astInfo["type"] = ast.Type().String()
	astInfo["expr_string"] = ast.String()

	var funcCalls []string
	var aggregations []string
	var binaryOps []string
	var vectors []string

	parser.Inspect(ast, func(node parser.Node, path []parser.Node) error {
		switch n := node.(type) {
		case *parser.Call:
			funcCalls = append(funcCalls, n.Func.Name)
		case *parser.AggregateExpr:
			aggregations = append(aggregations, n.Op.String())
		case *parser.BinaryExpr:
			binaryOps = append(binaryOps, n.Op.String())
		case *parser.VectorSelector:
			vectors = append(vectors, n.Name)
		}
		return nil
	})

	if len(funcCalls) > 0 {
		astInfo["functions"] = funcCalls
	}
	if len(aggregations) > 0 {
		astInfo["aggregations"] = aggregations
	}
	if len(binaryOps) > 0 {
		astInfo["binary_operators"] = binaryOps
	}
	if len(vectors) > 0 {
		astInfo["metrics"] = uniqueStrings(vectors)
	}

	return &ValidateResult{
		Valid:    true,
		ExprType: ast.Type().String(),
		ASTInfo:  astInfo,
		Message:  "PromQL syntax is valid",
	}
}

func uniqueStrings(s []string) []string {
	seen := make(map[string]bool)
	var result []string
	for _, v := range s {
		if !seen[v] {
			seen[v] = true
			result = append(result, v)
		}
	}
	return result
}

func SimulatePromQL(expr string, metrics []Metric) (*SimulateResult, error) {
	return SimulatePromQLWithDuration(expr, "", metrics, nil)
}

func SimulatePromQLWithDuration(expr string, forDuration string, metrics []Metric, timeSeries []TimeSeriesMetric) (*SimulateResult, error) {
	if _, err := ValidatePromQL(expr); err != nil {
		return nil, fmt.Errorf("invalid PromQL: %v", err)
	}

	result := &SimulateResult{
		Firing:           false,
		MatchedLabels:    []map[string]string{},
		Values:           []float64{},
		Timeline:         []TimelineEvent{},
		DurationVerified: false,
		RequiredDuration: forDuration,
	}

	comparison, value, metricSelector, err := parseAlertExpr(expr)
	if err != nil {
		return nil, err
	}

	for _, metric := range metrics {
		if matchesSelector(metric, metricSelector) {
			matched := evaluateComparison(metric.Value, comparison, value)
			if matched {
				result.Firing = true
				result.MatchedLabels = append(result.MatchedLabels, mergeLabels(metric.Name, metric.Labels))
				result.Values = append(result.Values, metric.Value)
			}
		}
	}

	if len(timeSeries) > 0 && forDuration != "" {
		duration, err := parseDuration(forDuration)
		if err != nil {
			return nil, fmt.Errorf("invalid duration format: %v", err)
		}

		matchedSeries, firing, actualDuration := evaluateTimeSeries(timeSeries, metricSelector, comparison, value, duration, result)
		result.MatchedTimeSeries = matchedSeries
		result.Firing = firing
		result.ActualDuration = actualDuration.String()
		result.DurationVerified = firing && actualDuration >= duration

		if result.Firing && result.DurationVerified {
			result.Message = fmt.Sprintf("Alert firing for %s! Duration condition met (%s required)", actualDuration, forDuration)
		} else if result.Firing {
			result.Message = fmt.Sprintf("Alert condition met but not for long enough. Firing for %s, needs %s", actualDuration, forDuration)
		} else {
			result.Message = "No metrics matched the alert condition during the time range"
		}
	} else if result.Firing {
		result.Message = fmt.Sprintf("Alert firing! %d metrics matched the condition", len(result.MatchedLabels))
	} else {
		result.Message = "No metrics matched the alert condition"
	}

	return result, nil
}

func evaluateTimeSeries(
	series []TimeSeriesMetric,
	sel *selector,
	comparison string,
	threshold float64,
	requiredDuration time.Duration,
	result *SimulateResult,
) ([]MatchedTimeSeries, bool, time.Duration) {
	var matchedSeries []MatchedTimeSeries
	anyFiring := false
	maxFiringDuration := time.Duration(0)

	now := time.Now()

	for _, ts := range series {
		metric := Metric{
			Name:   ts.Name,
			Labels: ts.Labels,
		}

		if !matchesSelector(metric, sel) {
			continue
		}

		matchedTS := MatchedTimeSeries{
			Name:       ts.Name,
			Labels:     ts.Labels,
			PointCount: len(ts.Points),
		}

		if len(ts.Points) == 0 {
			continue
		}

		var firingStart *time.Time
		var currentFiring bool
		var values []float64
		var timestamps []time.Time

		for i, point := range ts.Points {
			values = append(values, point.Value)
			timestamps = append(timestamps, point.Timestamp)

			matches := evaluateComparison(point.Value, comparison, threshold)

			if matches && !currentFiring {
				currentFiring = true
				startTime := point.Timestamp
				firingStart = &startTime
				matchedTS.Firing = true
				matchedTS.FiringStart = &startTime

				result.Timeline = append(result.Timeline, TimelineEvent{
					Timestamp: point.Timestamp,
					EventType: "start_firing",
					Message:   fmt.Sprintf("%s started firing at %.2f", ts.Name, point.Value),
				})
			} else if !matches && currentFiring {
				currentFiring = false
				duration := point.Timestamp.Sub(*firingStart)
				matchedTS.FiringFor = duration.String()

				if duration > maxFiringDuration {
					maxFiringDuration = duration
				}

				result.Timeline = append(result.Timeline, TimelineEvent{
					Timestamp: point.Timestamp,
					EventType: "stop_firing",
					Message:   fmt.Sprintf("%s stopped firing. Fired for %s", ts.Name, duration),
				})

				if duration >= requiredDuration {
					result.Timeline = append(result.Timeline, TimelineEvent{
						Timestamp: firingStart.Add(requiredDuration),
						EventType: "duration_met",
						Message:   fmt.Sprintf("%s met %s duration requirement", ts.Name, requiredDuration),
					})
				}

				firingStart = nil
			}

			if i == len(ts.Points)-1 && currentFiring && firingStart != nil {
				duration := now.Sub(*firingStart)
				matchedTS.FiringFor = duration.String()
				matchedTS.CurrentValue = point.Value

				if duration > maxFiringDuration {
					maxFiringDuration = duration
				}

				if duration >= requiredDuration {
					matchedTS.Firing = true
					anyFiring = true

					if duration-point.Timestamp.Sub(*firingStart) < requiredDuration {
						result.Timeline = append(result.Timeline, TimelineEvent{
							Timestamp: firingStart.Add(requiredDuration),
							EventType: "duration_met",
							Message:   fmt.Sprintf("%s met %s duration requirement", ts.Name, requiredDuration),
						})
					}
				}
			}
		}

		matchedTS.Values = values
		matchedTS.Timestamps = timestamps
		if len(values) > 0 {
			matchedTS.CurrentValue = values[len(values)-1]
		}

		matchedSeries = append(matchedSeries, matchedTS)

		if matchedTS.Firing {
			anyFiring = true
		}
	}

	return matchedSeries, anyFiring, maxFiringDuration
}

func parseDuration(durationStr string) (time.Duration, error) {
	durationStr = strings.TrimSpace(durationStr)
	if durationStr == "" {
		return 0, nil
	}

	var total time.Duration
	re := regexp.MustCompile(`(\d+)([smhdwy])`)
	matches := re.FindAllStringSubmatch(durationStr, -1)

	if len(matches) == 0 {
		return 0, fmt.Errorf("invalid duration: %s", durationStr)
	}

	for _, match := range matches {
		value, _ := strconv.Atoi(match[1])
		unit := match[2]

		switch unit {
		case "s":
			total += time.Duration(value) * time.Second
		case "m":
			total += time.Duration(value) * time.Minute
		case "h":
			total += time.Duration(value) * time.Hour
		case "d":
			total += time.Duration(value) * 24 * time.Hour
		case "w":
			total += time.Duration(value) * 7 * 24 * time.Hour
		case "y":
			total += time.Duration(value) * 365 * 24 * time.Hour
		default:
			return 0, fmt.Errorf("invalid duration unit: %s", unit)
		}
	}

	return total, nil
}

func parseAlertExpr(expr string) (string, float64, *selector, error) {
	comparisons := []string{">=", "<=", "!=", "==", ">", "<"}
	var comparison string
	var position int

	for _, op := range comparisons {
		if idx := strings.Index(expr, op); idx != -1 {
			if len(op) == 2 || (len(op) == 1 && (expr[idx-1:idx+1] != ">=" && expr[idx-1:idx+1] != "<=")) {
				comparison = op
				position = idx
				break
			}
		}
	}

	if comparison == "" {
		sel, err := parseSelector(expr)
		if err != nil {
			return "", 0, nil, err
		}
		return "!=", 0, sel, nil
	}

	leftPart := strings.TrimSpace(expr[:position])
	rightPart := strings.TrimSpace(expr[position+len(comparison):])

	value, err := strconv.ParseFloat(rightPart, 64)
	if err != nil {
		return "", 0, nil, fmt.Errorf("invalid threshold value: %s", rightPart)
	}

	sel, err := parseSelector(leftPart)
	if err != nil {
		return "", 0, nil, err
	}

	return comparison, value, sel, nil
}

func parseSelector(expr string) (*selector, error) {
	expr = strings.TrimSpace(expr)

	aggregations := []string{"sum", "avg", "min", "max", "count", "stddev", "stdvar", "topk", "bottomk"}
	for _, agg := range aggregations {
		if strings.HasPrefix(expr, agg+"(") {
			inner := expr[len(agg)+1 : len(expr)-1]
			parts := strings.SplitN(inner, ",", 2)
			if len(parts) == 2 {
				inner = parts[1]
			}
			return parseSelector(inner)
		}
	}

	ratePattern := regexp.MustCompile(`(rate|irate|increase|deriv|delta|idelta|resets|changes|predict_linear|holt_winters)\((.+)\[.+\](?:.+\))?\)`)
	if matches := ratePattern.FindStringSubmatch(expr); len(matches) > 0 {
		return parseSelector(matches[2])
	}

	aggByPattern := regexp.MustCompile(`(sum|avg|min|max|count|stddev|stdvar)\s+(by|without)\s*\(([^)]+)\)\s*\((.+)\)`)
	if matches := aggByPattern.FindStringSubmatch(expr); len(matches) > 0 {
		return parseSelector(matches[4])
	}

	namePattern := regexp.MustCompile(`^([a-zA-Z_:][a-zA-Z0-9_:]*)(\{.*\})?$`)
	matches := namePattern.FindStringSubmatch(expr)
	if matches == nil {
		return nil, fmt.Errorf("invalid metric selector: %s", expr)
	}

	sel := &selector{
		name:    matches[1],
		labels:  make(map[string]string),
		matches: make(map[string]*regexp.Regexp),
	}

	if matches[2] != "" {
		labelStr := matches[2][1 : len(matches[2])-1]
		labelPattern := regexp.MustCompile(`([a-zA-Z_][a-zA-Z0-9_]*)\s*(=~|=|!=|!~)\s*"([^"]*)"`)
		labelMatches := labelPattern.FindAllStringSubmatch(labelStr, -1)

		for _, lm := range labelMatches {
			key := lm[1]
			op := lm[2]
			val := lm[3]

			switch op {
			case "=":
				sel.labels[key] = val
			case "=~":
				r, err := regexp.Compile("^" + val + "$")
				if err != nil {
					return nil, fmt.Errorf("invalid regex for label %s: %v", key, err)
				}
				sel.matches[key] = r
			case "!=":
				sel.labels["!__"+key] = val
			case "!~":
				r, err := regexp.Compile("^" + val + "$")
				if err != nil {
					return nil, fmt.Errorf("invalid regex for label %s: %v", key, err)
				}
				sel.matches["!__"+key] = r
			}
		}
	}

	return sel, nil
}

func matchesSelector(metric Metric, sel *selector) bool {
	if sel.name != "" && metric.Name != sel.name {
		return false
	}

	for key, expected := range sel.labels {
		if strings.HasPrefix(key, "!__") {
			actualKey := strings.TrimPrefix(key, "!__")
			if metric.Labels[actualKey] == expected {
				return false
			}
		} else {
			if metric.Labels[key] != expected {
				return false
			}
		}
	}

	for key, regex := range sel.matches {
		if strings.HasPrefix(key, "!__") {
			actualKey := strings.TrimPrefix(key, "!__")
			if regex.MatchString(metric.Labels[actualKey]) {
				return false
			}
		} else {
			if !regex.MatchString(metric.Labels[key]) {
				return false
			}
		}
	}

	return true
}

func evaluateComparison(metricValue float64, comparison string, threshold float64) bool {
	if math.IsNaN(metricValue) {
		return false
	}

	switch comparison {
	case ">":
		return metricValue > threshold
	case ">=":
		return metricValue >= threshold
	case "<":
		return metricValue < threshold
	case "<=":
		return metricValue <= threshold
	case "==":
		return metricValue == threshold
	case "!=":
		return metricValue != threshold
	default:
		return metricValue > 0
	}
}

func mergeLabels(name string, labels map[string]string) map[string]string {
	result := make(map[string]string)
	for k, v := range labels {
		result[k] = v
	}
	result["__name__"] = name
	return result
}

func GenerateTimeSeries(name string, labels map[string]string, start time.Time, interval time.Duration, count int, valueFunc func(int) float64) TimeSeriesMetric {
	ts := TimeSeriesMetric{
		Name:   name,
		Labels: labels,
		Points: make([]TimeSeriesPoint, count),
	}

	for i := 0; i < count; i++ {
		ts.Points[i] = TimeSeriesPoint{
			Timestamp: start.Add(time.Duration(i) * interval),
			Value:     valueFunc(i),
		}
	}

	return ts
}
