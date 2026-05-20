package enhancements

import (
	"time"
)

type SLO struct {
	Name                 string        `json:"name" yaml:"name"`
	Description          string        `json:"description,omitempty" yaml:"description,omitempty"`
	TargetPercent        float64       `json:"target_percent" yaml:"target_percent"`
	Window               time.Duration `json:"window" yaml:"window"`
	TotalRequestsMetric  string        `json:"total_requests_metric" yaml:"total_requests_metric"`
	ErrorRequestsMetric  string        `json:"error_requests_metric" yaml:"error_requests_metric"`
	Labels               map[string]string `json:"labels,omitempty" yaml:"labels,omitempty"`
}

type SLOResult struct {
	SLOName               string  `json:"slo_name"`
	TargetPercent         float64 `json:"target_percent"`
	ActualPercent         float64 `json:"actual_percent"`
	ErrorBudgetPercent    float64 `json:"error_budget_percent"`
	ErrorBudgetRemaining  float64 `json:"error_budget_remaining_percent"`
	BurnRate              float64 `json:"burn_rate"`
	BurnRateStatus        string  `json:"burn_rate_status"`
	TotalRequests         float64 `json:"total_requests"`
	ErrorRequests         float64 `json:"error_requests"`
	TimeUntilBudgetExhausted string `json:"time_until_budget_exhausted,omitempty"`
}

type SLOManager struct {
	slos      map[string]SLO
	evaluator *SLOEvaluator
}

type SLOEvaluator struct {
	startTime time.Time
	endTime   time.Time
}

func NewSLOManager() *SLOManager {
	return &SLOManager{
		slos: make(map[string]SLO),
		evaluator: &SLOEvaluator{
			startTime: time.Now().Add(-30 * 24 * time.Hour),
			endTime:   time.Now(),
		},
	}
}

func (sm *SLOManager) AddSLO(s SLO) {
	sm.slos[s.Name] = s
}

func (sm *SLOManager) AddSLOs(slos []SLO) {
	for _, s := range slos {
		sm.slos[s.Name] = s
	}
}

func (sm *SLOManager) SetTimeRange(start, end time.Time) {
	sm.evaluator.startTime = start
	sm.evaluator.endTime = end
}

func (sm *SLOManager) EvaluateSLO(name string, totalRequests, errorRequests float64) *SLOResult {
	slo, exists := sm.slos[name]
	if !exists {
		return nil
	}

	if totalRequests == 0 {
		return &SLOResult{
			SLOName:             name,
			TargetPercent:       slo.TargetPercent,
			ActualPercent:       100.0,
			ErrorBudgetPercent:  100.0 - slo.TargetPercent,
			ErrorBudgetRemaining: 100.0 - slo.TargetPercent,
			BurnRate:            0,
			BurnRateStatus:      "healthy",
			TotalRequests:       0,
			ErrorRequests:       0,
		}
	}

	actualSuccessRate := ((totalRequests - errorRequests) / totalRequests) * 100
	errorBudgetPercent := 100.0 - slo.TargetPercent
	actualErrorPercent := 100.0 - actualSuccessRate

	burnRate := actualErrorPercent / errorBudgetPercent

	var status string
	switch {
	case burnRate <= 0.5:
		status = "healthy"
	case burnRate <= 1.0:
		status = "warning"
	case burnRate <= 2.0:
		status = "critical"
	default:
		status = "exhausted"
	}

	budgetRemainingPercent := errorBudgetPercent - actualErrorPercent
	if budgetRemainingPercent < 0 {
		budgetRemainingPercent = 0
	}

	var timeUntilExhausted string
	if burnRate > 0 && budgetRemainingPercent > 0 {
		duration := sm.evaluator.endTime.Sub(sm.evaluator.startTime)
		remainingDays := float64(duration.Hours()/24) * (budgetRemainingPercent / 100.0) / burnRate
		if remainingDays > 0 {
			timeUntilExhausted = time.Duration(remainingDays * 24 * float64(time.Hour)).String()
		}
	}

	return &SLOResult{
		SLOName:               name,
		TargetPercent:         slo.TargetPercent,
		ActualPercent:         actualSuccessRate,
		ErrorBudgetPercent:    errorBudgetPercent,
		ErrorBudgetRemaining:  budgetRemainingPercent,
		BurnRate:              burnRate,
		BurnRateStatus:        status,
		TotalRequests:         totalRequests,
		ErrorRequests:         errorRequests,
		TimeUntilBudgetExhausted: timeUntilExhausted,
	}
}

func (sm *SLOManager) EvaluateAll(totalRequests, errorRequests map[string]float64) []SLOResult {
	var results []SLOResult
	for name := range sm.slos {
		total := totalRequests[name]
		errors := errorRequests[name]
		result := sm.EvaluateSLO(name, total, errors)
		if result != nil {
			results = append(results, *result)
		}
	}
	return results
}

func (sm *SLOManager) GetSLO(name string) (SLO, bool) {
	s, ok := sm.slos[name]
	return s, ok
}

func (sm *SLOManager) GetAllSLOs() []SLO {
	var slos []SLO
	for _, s := range sm.slos {
		slos = append(slos, s)
	}
	return slos
}

func CreateAvailabilitySLO(name string, target9s float64) SLO {
	target := 100.0 - (100.0 / pow10(int(target9s)))
	return SLO{
		Name:                name,
		Description:         "Availability SLO with " + format9s(target9s) + " target",
		TargetPercent:       target,
		Window:              30 * 24 * time.Hour,
		TotalRequestsMetric: "http_requests_total",
		ErrorRequestsMetric: "http_requests_total{status=~\"5..\"}",
	}
}

func CreateLatencySLO(name string, targetPercent float64, threshold string) SLO {
	return SLO{
		Name:                name,
		Description:         "Latency SLO - " + threshold + " requests faster than threshold",
		TargetPercent:       targetPercent,
		Window:              30 * 24 * time.Hour,
		TotalRequestsMetric: "http_request_duration_seconds_count",
		ErrorRequestsMetric: "http_request_duration_seconds_bucket{le=\"" + threshold + "\"}",
	}
}

func pow10(n int) float64 {
	result := 1.0
	for i := 0; i < n; i++ {
		result *= 10
	}
	return result
}

func format9s(n float64) string {
	if n == 99.9 {
		return "Three 9s"
	} else if n == 99.99 {
		return "Four 9s"
	} else if n == 99.999 {
		return "Five 9s"
	}
	return "Custom"
}

func GenerateMultiBurnRateAlerts(sloName string, slo SLO) []BurnRateAlert {
	return []BurnRateAlert{
		{
			Name:        sloName + "BurnRatePage",
			Window:      1 * time.Hour,
			BurnRate:    14.4,
			Severity:    "page",
			Description: "Error budget burning 14.4x faster than expected",
		},
		{
			Name:        sloName + "BurnRateTicket",
			Window:      6 * time.Hour,
			BurnRate:    6,
			Severity:    "ticket",
			Description: "Error budget burning 6x faster than expected",
		},
		{
			Name:        sloName + "BurnRateSlow",
			Window:      3 * 24 * time.Hour,
			BurnRate:    1,
			Severity:    "warning",
			Description: "Error budget burning at expected rate",
		},
	}
}

type BurnRateAlert struct {
	Name        string        `json:"name"`
	Window      time.Duration `json:"window"`
	BurnRate    float64       `json:"burn_rate"`
	Severity    string        `json:"severity"`
	Description string        `json:"description"`
}
