package alert

import (
	"context"
	"fmt"
	"math"
	"os"
	"sort"
	"time"

	"github.com/prometheus/prometheus/model/labels"
	"github.com/prometheus/prometheus/model/rulefmt"
	"github.com/prometheus/prometheus/promql"
	"github.com/prometheus/prometheus/promql/parser"
	"github.com/prometheus/prometheus/storage"
	"gopkg.in/yaml.v3"
)

type SyntaxError struct {
	AlertName string `json:"alert_name"`
	Error     string `json:"error"`
	Line      int    `json:"line,omitempty"`
}

type AlertState string

const (
	StateInactive AlertState = "inactive"
	StatePending  AlertState = "pending"
	StateFiring   AlertState = "firing"
	StateResolved AlertState = "resolved"
)

type AlertResult struct {
	AlertName   string            `json:"alert_name"`
	Labels      map[string]string `json:"labels"`
	Annotations map[string]string `json:"annotations"`
	State       AlertState        `json:"state"`
	Value       float64           `json:"value"`
	FirstActive time.Time         `json:"first_active"`
	FiredAt     time.Time         `json:"fired_at,omitempty"`
	ResolvedAt  time.Time         `json:"resolved_at,omitempty"`
	Duration    time.Duration     `json:"duration_seconds,omitempty"`
}

type RuleEvaluation struct {
	RuleName    string
	ForDuration time.Duration
	Labels      map[string]string
	Annotations map[string]string
	States      []EvaluationPoint
	Passed      bool
	Error       error
}

type EvaluationPoint struct {
	Timestamp time.Time
	Value     float64
	Active    bool
}

type TimeSeries struct {
	Labels labels.Labels
	Points []TimeSeriesPoint
}

type TimeSeriesPoint struct {
	Timestamp int64
	Value     float64
}

type Validator struct {
	groups         []rulefmt.RuleGroup
	errors         []SyntaxError
	resolveDelay   time.Duration
	evalTimestamps []int64
}

func NewValidator() *Validator {
	return &Validator{
		resolveDelay: 5 * time.Minute,
	}
}

func (v *Validator) SetResolveDelay(d time.Duration) {
	v.resolveDelay = d
}

func (v *Validator) SetEvalTimestamps(ts []int64) {
	v.evalTimestamps = ts
}

func (v *Validator) LoadRules(filename string) error {
	data, err := os.ReadFile(filename)
	if err != nil {
		return fmt.Errorf("failed to read rules file: %w", err)
	}

	var groups rulefmt.RuleGroups
	if err := yaml.Unmarshal(data, &groups); err != nil {
		return fmt.Errorf("failed to parse rules yaml: %w", err)
	}

	v.groups = groups.Groups
	return nil
}

func (v *Validator) CheckSyntax() []SyntaxError {
	v.errors = nil

	for _, group := range v.groups {
		for i, rule := range group.Rules {
			if rule.Alert != "" {
				if _, err := parser.ParseExpr(rule.Expr.Value); err != nil {
					v.errors = append(v.errors, SyntaxError{
						AlertName: rule.Alert,
						Error:     err.Error(),
						Line:      i + 1,
					})
				}

				if err := v.validateLabels(rule.Labels); err != nil {
					v.errors = append(v.errors, SyntaxError{
						AlertName: rule.Alert,
						Error:     fmt.Sprintf("invalid labels: %v", err),
						Line:      i + 1,
					})
				}

				if err := v.validateAnnotations(rule.Annotations); err != nil {
					v.errors = append(v.errors, SyntaxError{
						AlertName: rule.Alert,
						Error:     fmt.Sprintf("invalid annotations: %v", err),
						Line:      i + 1,
					})
				}
			}
		}
	}

	return v.errors
}

func (v *Validator) validateLabels(lbls map[string]string) error {
	for k := range lbls {
		if !labels.LabelNameRE.MatchString(k) {
			return fmt.Errorf("invalid label name: %s", k)
		}
	}
	return nil
}

func (v *Validator) validateAnnotations(anns map[string]string) error {
	for k := range anns {
		if !labels.LabelNameRE.MatchString(k) {
			return fmt.Errorf("invalid annotation name: %s", k)
		}
	}
	return nil
}

func (v *Validator) EvaluateRules(series []TimeSeries) ([]RuleEvaluation, error) {
	var results []RuleEvaluation

	queryable := newMemQueryable(series)
	engine := promql.NewEngine(promql.EngineOpts{
		MaxSamples:         50000000,
		Timeout:            time.Minute,
		LookbackDelta:      5 * time.Minute,
		EnableAtModifier:   true,
		EnableNegativeOffset: true,
	})

	for _, group := range v.groups {
		for _, rule := range group.Rules {
			if rule.Alert == "" {
				continue
			}

			forDuration, _ := time.ParseDuration(rule.For)
			if forDuration == 0 {
				forDuration = 0
			}

			eval := RuleEvaluation{
				RuleName:    rule.Alert,
				ForDuration: forDuration,
				Labels:      rule.Labels,
				Annotations: rule.Annotations,
				Passed:      true,
			}

			activeSeries := make(map[string][]EvaluationPoint)

			for _, ts := range v.evalTimestamps {
				evalTime := time.UnixMilli(ts)
				
				qry, err := engine.NewInstantQuery(queryable, nil, rule.Expr.Value, evalTime)
				if err != nil {
					eval.Passed = false
					eval.Error = fmt.Errorf("query creation failed: %w", err)
					break
				}

				res := qry.Exec(context.Background())
				if res.Err != nil {
					eval.Passed = false
					eval.Error = fmt.Errorf("query execution failed: %w", res.Err)
					qry.Close()
					break
				}

				vec, ok := res.Value.(promql.Vector)
				if ok {
					for _, sample := range vec {
						lblKey := sample.Metric.String()
						activeSeries[lblKey] = append(activeSeries[lblKey], EvaluationPoint{
							Timestamp: evalTime,
							Value:     sample.V,
							Active:    true,
						})
					}
				}

				qry.Close()
			}

			for lblKey, points := range activeSeries {
				states := v.evaluateAlertState(points, forDuration)
				eval.States = append(eval.States, states...)
			}

			results = append(results, eval)
		}
	}

	return results, nil
}

func (v *Validator) evaluateAlertState(points []EvaluationPoint, forDuration time.Duration) EvaluationPoint {
	if len(points) == 0 {
		return EvaluationPoint{}
	}

	sort.Slice(points, func(i, j int) bool {
		return points[i].Timestamp.Before(points[j].Timestamp)
	})

	var firstActive time.Time
	var lastActive time.Time
	continuousActive := 0

	for i, p := range points {
		if p.Active {
			if firstActive.IsZero() {
				firstActive = p.Timestamp
			}
			lastActive = p.Timestamp
			continuousActive++
		} else {
			if i > 0 && points[i-1].Active && forDuration > 0 {
				continuousActive = 0
			}
		}
	}

	lastPoint := points[len(points)-1]
	result := EvaluationPoint{
		Timestamp: lastPoint.Timestamp,
		Value:     lastPoint.Value,
		Active:    lastPoint.Active,
	}

	return result
}

func (v *Validator) GenerateAlertResults(evals []RuleEvaluation) []AlertResult {
	var results []AlertResult

	for _, eval := range evals {
		if eval.Error != nil || len(eval.States) == 0 {
			continue
		}

		var firstActive, firedAt, resolvedAt time.Time
		currentState := StateInactive
		consecutiveActive := 0

		for _, p := range eval.States {
			if p.Active {
				if firstActive.IsZero() {
					firstActive = p.Timestamp
				}
				consecutiveActive++
				
				if eval.ForDuration == 0 {
					currentState = StateFiring
					if firedAt.IsZero() {
						firedAt = p.Timestamp
					}
				} else {
					duration := p.Timestamp.Sub(firstActive)
					if duration >= eval.ForDuration {
						if currentState != StateFiring {
							firedAt = p.Timestamp
						}
						currentState = StateFiring
					} else if currentState == StateInactive {
						currentState = StatePending
					}
				}
			} else {
				if currentState == StateFiring || currentState == StatePending {
					if !firedAt.IsZero() {
						resolvedAt = p.Timestamp
						currentState = StateResolved
					} else {
						currentState = StateInactive
						firstActive = time.Time{}
					}
				}
				consecutiveActive = 0
			}
		}

		if currentState != StateInactive {
			alertResult := AlertResult{
				AlertName:   eval.RuleName,
				State:       currentState,
				Labels:      make(map[string]string),
				Annotations: eval.Annotations,
				FirstActive: firstActive,
				FiredAt:     firedAt,
				ResolvedAt:  resolvedAt,
			}

			for k, v := range eval.Labels {
				alertResult.Labels[k] = v
			}
			alertResult.Labels["alertname"] = eval.RuleName

			if len(eval.States) > 0 {
				alertResult.Value = eval.States[len(eval.States)-1].Value
			}

			if !resolvedAt.IsZero() {
				alertResult.Duration = resolvedAt.Sub(firedAt)
			} else if !firedAt.IsZero() {
				alertResult.Duration = time.Since(firedAt)
			}

			results = append(results, alertResult)
		}
	}

	return results
}

type memQueryable struct {
	series []TimeSeries
}

func newMemQueryable(series []TimeSeries) *memQueryable {
	return &memQueryable{series: series}
}

func (q *memQueryable) Querier(ctx context.Context, mint, maxt int64) (storage.Querier, error) {
	return &memQuerier{series: q.series, mint: mint, maxt: maxt}, nil
}

type memQuerier struct {
	series []TimeSeries
	mint   int64
	maxt   int64
}

func (q *memQuerier) Select(ctx context.Context, sortSeries bool, hints *storage.SelectHints, matchers ...*labels.Matcher) storage.SeriesSet {
	var matched []storage.Series
	
	for _, s := range q.series {
		matchedAll := true
		for _, matcher := range matchers {
			if !matcher.Matches(s.Labels.Get(matcher.Name)) {
				matchedAll = false
				break
			}
		}
		if matchedAll {
			filteredPoints := make([]TimeSeriesPoint, 0)
			for _, p := range s.Points {
				if p.Timestamp >= q.mint && p.Timestamp <= q.maxt {
					filteredPoints = append(filteredPoints, p)
				}
			}
			if len(filteredPoints) > 0 {
				matched = append(matched, &memSeries{
					labels: s.Labels,
					points: filteredPoints,
				})
			} else if len(s.Points) > 0 {
				matched = append(matched, &memSeries{
					labels: s.Labels,
					points: s.Points,
				})
			}
		}
	}
	
	return &memSeriesSet{series: matched}
}

func (q *memQuerier) LabelValues(name string, matchers ...*labels.Matcher) ([]string, storage.Warnings, error) {
	values := make(map[string]struct{})
	for _, s := range q.series {
		if v := s.Labels.Get(name); v != "" {
			values[v] = struct{}{}
		}
	}
	var result []string
	for v := range values {
		result = append(result, v)
	}
	return result, nil, nil
}

func (q *memQuerier) LabelNames(matchers ...*labels.Matcher) ([]string, storage.Warnings, error) {
	names := make(map[string]struct{})
	for _, s := range q.series {
		for _, l := range s.Labels {
			names[l.Name] = struct{}{}
		}
	}
	var result []string
	for n := range names {
		result = append(result, n)
	}
	return result, nil, nil
}

func (q *memQuerier) Close() error {
	return nil
}

type memSeriesSet struct {
	series []storage.Series
	idx    int
}

func (s *memSeriesSet) Next() bool {
	s.idx++
	return s.idx <= len(s.series)
}

func (s *memSeriesSet) At() storage.Series {
	if s.idx == 0 || s.idx > len(s.series) {
		return nil
	}
	return s.series[s.idx-1]
}

func (s *memSeriesSet) Err() error {
	return nil
}

func (s *memSeriesSet) Warnings() storage.Warnings {
	return nil
}

type memSeries struct {
	labels labels.Labels
	points []TimeSeriesPoint
}

func (s *memSeries) Labels() labels.Labels {
	return s.labels
}

func (s *memSeries) Iterator(it storage.SeriesIterator) storage.SeriesIterator {
	return &memSeriesIterator{points: s.points, idx: -1}
}

type memSeriesIterator struct {
	points []TimeSeriesPoint
	idx    int
}

func (it *memSeriesIterator) Seek(t int64) bool {
	for i, p := range it.points {
		if p.Timestamp >= t {
			it.idx = i
			return true
		}
	}
	it.idx = len(it.points)
	return false
}

func (it *memSeriesIterator) At() (t int64, v float64) {
	if it.idx < 0 || it.idx >= len(it.points) {
		return math.MaxInt64, 0
	}
	p := it.points[it.idx]
	return p.Timestamp, p.Value
}

func (it *memSeriesIterator) Next() bool {
	it.idx++
	return it.idx < len(it.points)
}

func (it *memSeriesIterator) Err() error {
	return nil
}
