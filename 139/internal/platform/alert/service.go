package alert

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"prometheus-alert-tester/internal/platform/query"

	"github.com/prometheus/prometheus/model/rulefmt"
	"gopkg.in/yaml.v3"
)

type Service struct {
	queryService *query.Service
	rules        map[string]*Rule
	alerts       map[string]*Alert
	history      []*AlertHistory
	mu           sync.RWMutex
}

type Rule struct {
	ID         string                 `json:"id"`
	Name       string                 `json:"name"`
	Expr       string                 `json:"expr"`
	For        string                 `json:"for,omitempty"`
	Labels     map[string]string      `json:"labels,omitempty"`
	Annotations map[string]string     `json:"annotations,omitempty"`
	Source     string                 `json:"source,omitempty"`
	CreatedAt  time.Time              `json:"created_at"`
}

type Alert struct {
	ID          string            `json:"id"`
	RuleID      string            `json:"rule_id"`
	Name        string            `json:"name"`
	State       string            `json:"state"`
	Value       float64           `json:"value"`
	Labels      map[string]string `json:"labels"`
	Annotations map[string]string `json:"annotations"`
	ActiveAt    time.Time         `json:"active_at"`
	FiredAt     time.Time         `json:"fired_at,omitempty"`
	ResolvedAt  time.Time         `json:"resolved_at,omitempty"`
}

type AlertHistory struct {
	ID         string    `json:"id"`
	AlertName  string    `json:"alert_name"`
	State      string    `json:"state"`
	Value      float64   `json:"value"`
	Timestamp  time.Time `json:"timestamp"`
}

type TestRequest struct {
	Expr      string        `json:"expr"`
	For       string        `json:"for,omitempty"`
	TimeRange TimeRange     `json:"time_range,omitempty"`
}

type TimeRange struct {
	Start time.Time `json:"start"`
	End   time.Time `json:"end"`
	Step  string    `json:"step"`
}

type TestResult struct {
	Valid          bool             `json:"valid"`
	ParseError     string           `json:"parse_error,omitempty"`
	States         []TestStatePoint `json:"states"`
	TotalPoints    int              `json:"total_points"`
	TruePoints     int              `json:"true_points"`
	FalsePoints    int              `json:"false_points"`
	WouldFire      bool             `json:"would_fire"`
	FireDuration   string           `json:"fire_duration,omitempty"`
}

type TestStatePoint struct {
	Timestamp time.Time `json:"timestamp"`
	Value     float64   `json:"value"`
	Active    bool      `json:"active"`
}

type UploadRulesRequest struct {
	YAML string `json:"yaml"`
}

func NewService(qs *query.Service) *Service {
	return &Service{
		queryService: qs,
		rules:        make(map[string]*Rule),
		alerts:       make(map[string]*Alert),
	}
}

func (s *Service) GetRules() []*Rule {
	s.mu.RLock()
	defer s.mu.RUnlock()

	rules := make([]*Rule, 0, len(s.rules))
	for _, r := range s.rules {
		rules = append(rules, r)
	}
	return rules
}

func (s *Service) UploadRules(yamlContent string) error {
	var groups rulefmt.RuleGroups
	if err := yaml.Unmarshal([]byte(yamlContent), &groups); err != nil {
		return fmt.Errorf("failed to parse rules yaml: %w", err)
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	for _, group := range groups.Groups {
		for _, rule := range group.Rules {
			if rule.Alert.Value != "" {
				id := generateRuleID(rule.Alert.Value)
				s.rules[id] = &Rule{
					ID:         id,
					Name:       rule.Alert.Value,
					Expr:       rule.Expr.Value,
					For:        rule.For,
					Labels:     rule.Labels,
					Annotations: rule.Annotations,
					Source:     group.Name,
					CreatedAt:  time.Now(),
				}
			}
		}
	}

	return nil
}

func (s *Service) DeleteRule(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.rules[id]; !exists {
		return fmt.Errorf("rule not found: %s", id)
	}

	delete(s.rules, id)
	return nil
}

func (s *Service) GetActiveAlerts() []*Alert {
	s.mu.RLock()
	defer s.mu.RUnlock()

	alerts := make([]*Alert, 0, len(s.alerts))
	for _, a := range s.alerts {
		if a.State != "resolved" {
			alerts = append(alerts, a)
		}
	}
	return alerts
}

func (s *Service) GetHistory() []*AlertHistory {
	s.mu.RLock()
	defer s.mu.RUnlock()

	return append([]*AlertHistory{}, s.history...)
}

func (s *Service) TestAlert(req *TestRequest) (*TestResult, error) {
	result := &TestResult{
		Valid: true,
	}

	if _, err := s.queryService.ParseQuery(req.Expr); err != nil {
		result.Valid = false
		result.ParseError = err.Error()
		return result, nil
	}

	startTime := req.TimeRange.Start
	if startTime.IsZero() {
		startTime = time.Now().Add(-1 * time.Hour)
	}
	endTime := req.TimeRange.End
	if endTime.IsZero() {
		endTime = time.Now()
	}
	step := req.TimeRange.Step
	if step == "" {
		step = "1m"
	}

	queryResult, err := s.queryService.QueryRange(nil, req.Expr,
		startTime.Format(time.RFC3339),
		endTime.Format(time.RFC3339),
		step)
	if err != nil {
		return nil, fmt.Errorf("failed to execute query: %w", err)
	}

	if queryResult.Status != "success" {
		return nil, fmt.Errorf("query failed: %s", queryResult.Error)
	}

	var matrix query.MatrixResult
	if err := json.Unmarshal(queryResult.Data.Result, &matrix); err != nil {
		return nil, fmt.Errorf("failed to parse matrix result: %w", err)
	}

	for _, series := range matrix {
		for _, val := range series.Values {
			ts, _ := val[0].(float64)
			value, _ := val[1].(float64)
			active := value != 0

			point := TestStatePoint{
				Timestamp: time.Unix(int64(ts), 0),
				Value:     value,
				Active:    active,
			}
			result.States = append(result.States, point)

			result.TotalPoints++
			if active {
				result.TruePoints++
			} else {
				result.FalsePoints++
			}
		}
	}

	forDuration, _ := time.ParseDuration(req.For)
	if forDuration > 0 && len(result.States) > 0 {
		consecutive := 0
		for i, state := range result.States {
			if state.Active {
				consecutive++
				if i > 0 {
					duration := state.Timestamp.Sub(result.States[i-consecutive].Timestamp)
					if duration >= forDuration {
						result.WouldFire = true
						result.FireDuration = duration.String()
						break
					}
				}
			} else {
				consecutive = 0
			}
		}
	} else if result.TruePoints > 0 {
		result.WouldFire = true
	}

	return result, nil
}

func generateRuleID(name string) string {
	h := sha256.New()
	h.Write([]byte(name + time.Now().String()))
	return hex.EncodeToString(h.Sum(nil))[:8]
}
