package report

import (
	"encoding/json"
	"fmt"
	"os"
	"time"

	"prometheus-alert-tester/internal/alert"
	"prometheus-alert-tester/internal/enhancements"
)

type TestStats struct {
	TotalRules          int                   `json:"total_rules"`
	PassedRules         int                   `json:"passed_rules"`
	FailedRules         int                   `json:"failed_rules"`
	PassRate            float64               `json:"pass_rate"`
	AlertsFiring        int                   `json:"alerts_firing"`
	AlertsPending       int                   `json:"alerts_pending"`
	AlertsResolved      int                   `json:"alerts_resolved"`
	AlertsSilenced      int                   `json:"alerts_silenced,omitempty"`
	AverageFiringTime   float64               `json:"average_firing_time_seconds,omitempty"`
	SLOViolations       int                   `json:"slo_violations,omitempty"`
}

type FailedRuleDetail struct {
	RuleName    string `json:"rule_name"`
	Error       string `json:"error,omitempty"`
	Expected    string `json:"expected,omitempty"`
	ActualState string `json:"actual_state,omitempty"`
}

type TimeRange struct {
	Start time.Time `json:"start"`
	End   time.Time `json:"end"`
	Step  string    `json:"step"`
}

type ClusterReport struct {
	Clusters       []enhancements.Cluster `json:"clusters"`
	EnabledCount   int                    `json:"enabled_count"`
	TotalCount     int                    `json:"total_count"`
	HealthStatus   map[string]string      `json:"health_status,omitempty"`
}

type Report struct {
	Timestamp       time.Time              `json:"timestamp"`
	RulesFile       string                 `json:"rules_file"`
	MetricsFile     string                 `json:"metrics_file,omitempty"`
	TestDuration    time.Duration          `json:"test_duration_seconds"`
	TimeRange       TimeRange              `json:"time_range"`
	Stats           TestStats              `json:"statistics"`
	SyntaxErrors    []alert.SyntaxError    `json:"syntax_errors,omitempty"`
	Alerts          []alert.AlertResult    `json:"alerts,omitempty"`
	FailedDetails   []FailedRuleDetail     `json:"failed_rule_details,omitempty"`
	SilencedAlerts  []string               `json:"silenced_alerts,omitempty"`
	SLOResults     []*enhancements.SLOResult `json:"slo_results,omitempty"`
	ClusterReport  *ClusterReport          `json:"cluster_report,omitempty"`
}

func NewReport() *Report {
	return &Report{
		Timestamp: time.Now(),
	}
}

func (r *Report) SetTimeRange(start, end time.Time, step time.Duration) {
	r.TimeRange = TimeRange{
		Start: start,
		End:   end,
		Step:  step.String(),
	}
}

func (r *Report) CalculateStats(evals []alert.RuleEvaluation, alerts []alert.AlertResult) {
	r.Stats.TotalRules = len(evals)

	for _, eval := range evals {
		if eval.Passed && eval.Error == nil {
			r.Stats.PassedRules++
		} else {
			r.Stats.FailedRules++
		}
	}

	if r.Stats.TotalRules > 0 {
		r.Stats.PassRate = float64(r.Stats.PassedRules) / float64(r.Stats.TotalRules) * 100
	}

	for _, a := range alerts {
		switch a.State {
		case alert.StateFiring:
			r.Stats.AlertsFiring++
		case alert.StatePending:
			r.Stats.AlertsPending++
		case alert.StateResolved:
			r.Stats.AlertsResolved++
		}
	}

	var totalFiringTime float64
	var firingCount int
	for _, a := range alerts {
		if a.State == alert.StateFiring || a.State == alert.StateResolved {
			if a.Duration > 0 {
				totalFiringTime += float64(a.Duration.Seconds())
				firingCount++
			}
		}
	}
	if firingCount > 0 {
		r.Stats.AverageFiringTime = totalFiringTime / float64(firingCount)
	}

	if len(r.SilencedAlerts) > 0 {
		r.Stats.AlertsSilenced = len(r.SilencedAlerts)
	}

	if len(r.SLOResults) > 0 {
		for _, slo := range r.SLOResults {
			if slo != nil && slo.BurnRateStatus != "healthy" {
				r.Stats.SLOViolations++
			}
		}
	}
}

func (r *Report) AddFailedRuleDetails(evals []alert.RuleEvaluation) {
	for _, eval := range evals {
		if !eval.Passed || eval.Error != nil {
			detail := FailedRuleDetail{
				RuleName: eval.RuleName,
			}
			if eval.Error != nil {
				detail.Error = eval.Error.Error()
			}
			r.FailedDetails = append(r.FailedDetails, detail)
		}
	}
}

func (r *Report) SaveToFile(filename string) error {
	data, err := json.MarshalIndent(r, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to marshal report: %w", err)
	}

	if err := os.WriteFile(filename, data, 0644); err != nil {
		return fmt.Errorf("failed to write report file: %w", err)
	}

	return nil
}

func (r *Report) PrintSummary() {
	fmt.Println("\n" + "="*70)
	fmt.Println("PROMETHEUS ALERT TESTER - TEST REPORT")
	fmt.Println("="*70)
	fmt.Printf("Test Time: %s\n", r.Timestamp.Format(time.RFC3339))
	fmt.Printf("Rules File: %s\n", r.RulesFile)
	if r.MetricsFile != "" {
		fmt.Printf("Metrics File: %s\n", r.MetricsFile)
	}
	fmt.Printf("Test Duration: %v\n", r.TestDuration.Round(time.Millisecond))
	fmt.Printf("Time Range: %s to %s (step: %s)\n",
		r.TimeRange.Start.Format("15:04:05"),
		r.TimeRange.End.Format("15:04:05"),
		r.TimeRange.Step)

	fmt.Println("\n--- RULE EVALUATION STATISTICS ---")
	fmt.Printf("  Total Rules Evaluated: %d\n", r.Stats.TotalRules)
	fmt.Printf("  Passed: %d (%.2f%%)\n", r.Stats.PassedRules, r.Stats.PassRate)
	fmt.Printf("  Failed: %d\n", r.Stats.FailedRules)

	fmt.Println("\n--- ALERT STATE SUMMARY ---")
	fmt.Printf("  Firing: %d\n", r.Stats.AlertsFiring)
	fmt.Printf("  Pending: %d\n", r.Stats.AlertsPending)
	fmt.Printf("  Resolved: %d\n", r.Stats.AlertsResolved)
	if r.Stats.AlertsSilenced > 0 {
		fmt.Printf("  Silenced: %d\n", r.Stats.AlertsSilenced)
	}
	if r.Stats.AverageFiringTime > 0 {
		fmt.Printf("  Average Firing Duration: %.1f seconds\n", r.Stats.AverageFiringTime)
	}

	if len(r.Alerts) > 0 {
		fmt.Println("\n--- ACTIVE ALERTS ---")
		for i, a := range r.Alerts {
			if i >= 10 {
				fmt.Printf("  ... and %d more alerts\n", len(r.Alerts)-10)
				break
			}
			statusSymbol := "✗"
			if a.State == alert.StateResolved {
				statusSymbol = "✓"
			} else if a.State == alert.StatePending {
				statusSymbol = "⚡"
			}
			fmt.Printf("  %s [%s] %s (value: %.2f)\n", statusSymbol, a.State, a.AlertName, a.Value)
		}
	}

	if len(r.SLOResults) > 0 {
		fmt.Println("\n--- SLO BURN RATE RESULTS ---")
		for _, slo := range r.SLOResults {
			if slo == nil {
				continue
			}
			statusSymbol := "✓"
			if slo.BurnRateStatus != "healthy" {
				statusSymbol = "⚠"
			}
			fmt.Printf("  %s %s - %.2f%% SLO target\n", statusSymbol, slo.SLOName, slo.TargetPercent)
			fmt.Printf("    Actual: %.2f%% | Error Budget: %.2f%% | Burn Rate: %.2fx\n",
				slo.ActualPercent, slo.ErrorBudgetRemaining, slo.BurnRate)
			fmt.Printf("    Status: %s\n", slo.BurnRateStatus)
		}
	}

	if r.ClusterReport != nil {
		fmt.Println("\n--- MULTI-CLUSTER SUMMARY ---")
		fmt.Printf("  Total Clusters: %d\n", r.ClusterReport.TotalCount)
		fmt.Printf("  Enabled Clusters: %d\n", r.ClusterReport.EnabledCount)
		if len(r.ClusterReport.HealthStatus) > 0 {
			fmt.Println("  Cluster Health:")
			for name, status := range r.ClusterReport.HealthStatus {
				statusSymbol := "✓"
				if status != "healthy" {
					statusSymbol = "⚠"
				}
				fmt.Printf("    %s %s: %s\n", statusSymbol, name, status)
			}
		}
	}

	if len(r.SyntaxErrors) > 0 {
		fmt.Println("\n--- SYNTAX ERRORS ---")
		for _, err := range r.SyntaxErrors {
			fmt.Printf("  ✗ %s: %s\n", err.AlertName, err.Error)
		}
	}

	if len(r.FailedDetails) > 0 {
		fmt.Println("\n--- FAILED RULE DETAILS ---")
		for _, d := range r.FailedDetails {
			if d.Error != "" {
				fmt.Printf("  ✗ %s: %s\n", d.RuleName, d.Error)
			} else {
				fmt.Printf("  ✗ %s: evaluation failed\n", d.RuleName)
			}
		}
	}

	fmt.Println("\n" + "="*70)
}
