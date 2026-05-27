package report

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/cloud-migration-tool/pkg/cloud"
)

type ReportFormat string

const (
	FormatJSON   ReportFormat = "json"
	FormatHTML   ReportFormat = "html"
	FormatMarkdown ReportFormat = "markdown"
	FormatText   ReportFormat = "text"
)

type MigrationReport struct {
	ReportID      string                 `json:"report_id"`
	GeneratedAt   time.Time              `json:"generated_at"`
	SourceCloud   string                 `json:"source_cloud"`
	SourceRegion  string                 `json:"source_region"`
	DestCloud     string                 `json:"dest_cloud"`
	DestRegion    string                 `json:"dest_region"`
	OverallStatus string                 `json:"overall_status"`
	Tasks         []TaskReport           `json:"tasks"`
	Summary       Summary                `json:"summary"`
	CostEstimate  CostEstimate           `json:"cost_estimate"`
	Recommendations []string             `json:"recommendations"`
}

type TaskReport struct {
	TaskID      string                 `json:"task_id"`
	TaskType    string                 `json:"task_type"`
	ResourceName string                `json:"resource_name"`
	Status      string                 `json:"status"`
	Progress    float64                `json:"progress"`
	StartTime   time.Time              `json:"start_time"`
	EndTime     time.Time              `json:"end_time"`
	Duration    string                 `json:"duration"`
	SourceInfo  map[string]interface{} `json:"source_info"`
	TargetInfo  map[string]interface{} `json:"target_info"`
	Message     string                 `json:"message"`
	Errors      []string               `json:"errors,omitempty"`
}

type Summary struct {
	TotalTasks      int     `json:"total_tasks"`
	CompletedTasks  int     `json:"completed_tasks"`
	FailedTasks     int     `json:"failed_tasks"`
	RunningTasks    int     `json:"running_tasks"`
	SuccessRate     float64 `json:"success_rate"`
	TotalDuration   string  `json:"total_duration"`
	DataTransferred int64   `json:"data_transferred_bytes"`
}

type CostEstimate struct {
	SourceEgressCost   float64 `json:"source_egress_cost_usd"`
	DestIngressCost    float64 `json:"dest_ingress_cost_usd"`
	ComputeCost        float64 `json:"compute_cost_usd"`
	StorageCost        float64 `json:"storage_cost_usd"`
	TotalEstimatedCost float64 `json:"total_estimated_cost_usd"`
	Currency           string  `json:"currency"`
}

type ReportGenerator struct {
	tasks   map[string]*cloud.MigrationStatus
	reports []MigrationReport
}

func NewReportGenerator() *ReportGenerator {
	return &ReportGenerator{
		tasks:   make(map[string]*cloud.MigrationStatus),
		reports: make([]MigrationReport, 0),
	}
}

func (rg *ReportGenerator) AddTaskStatus(status *cloud.MigrationStatus) {
	rg.tasks[status.TaskID] = status
}

func (rg *ReportGenerator) GenerateReport(
	sourceCloud, sourceRegion,
	destCloud, destRegion string,
) *MigrationReport {
	report := &MigrationReport{
		ReportID:     fmt.Sprintf("report-%d", time.Now().Unix()),
		GeneratedAt:  time.Now(),
		SourceCloud:  sourceCloud,
		SourceRegion: sourceRegion,
		DestCloud:    destCloud,
		DestRegion:   destRegion,
		Tasks:        make([]TaskReport, 0),
	}

	completed := 0
	failed := 0
	running := 0

	for _, task := range rg.tasks {
		taskReport := rg.convertToTaskReport(task)
		report.Tasks = append(report.Tasks, taskReport)

		switch task.Status {
		case "completed":
			completed++
		case "failed":
			failed++
		case "running":
			running++
		}
	}

	report.Summary = Summary{
		TotalTasks:     len(rg.tasks),
		CompletedTasks: completed,
		FailedTasks:    failed,
		RunningTasks:   running,
		SuccessRate:    0,
	}

	if len(rg.tasks) > 0 {
		report.Summary.SuccessRate = float64(completed) / float64(len(rg.tasks))
	}

	if failed > 0 {
		report.OverallStatus = "failed"
	} else if running > 0 {
		report.OverallStatus = "in_progress"
	} else {
		report.OverallStatus = "completed"
	}

	report.CostEstimate = rg.estimateCosts()
	report.Recommendations = rg.generateRecommendations(report)

	rg.reports = append(rg.reports, *report)
	return report
}

func (rg *ReportGenerator) convertToTaskReport(status *cloud.MigrationStatus) TaskReport {
	startTime := time.Unix(status.StartTime, 0)
	endTime := time.Unix(status.EndTime, 0)
	duration := endTime.Sub(startTime)

	if status.EndTime == 0 {
		duration = time.Since(startTime)
	}

	return TaskReport{
		TaskID:       status.TaskID,
		TaskType:     rg.getTaskType(status.TaskID),
		ResourceName: rg.getResourceName(status.SourceInfo),
		Status:       status.Status,
		Progress:     status.Progress,
		StartTime:    startTime,
		EndTime:      endTime,
		Duration:     duration.String(),
		SourceInfo:   status.SourceInfo,
		TargetInfo:   status.TargetInfo,
		Message:      status.Message,
	}
}

func (rg *ReportGenerator) getTaskType(taskID string) string {
	switch {
	case strings.HasPrefix(taskID, "compute-"):
		return "compute"
	case strings.HasPrefix(taskID, "database-"):
		return "database"
	case strings.HasPrefix(taskID, "storage-"):
		return "storage"
	default:
		return "unknown"
	}
}

func (rg *ReportGenerator) getResourceName(info map[string]interface{}) string {
	if instanceID, ok := info["instance_id"].(string); ok {
		return instanceID
	}
	if bucket, ok := info["source_bucket"].(string); ok {
		return bucket
	}
	if dbID, ok := info["db_instance_id"].(string); ok {
		return dbID
	}
	return "unknown"
}

func (rg *ReportGenerator) estimateCosts() CostEstimate {
	return CostEstimate{
		SourceEgressCost:   0.09,
		DestIngressCost:    0.00,
		ComputeCost:        2.50,
		StorageCost:        0.23,
		TotalEstimatedCost: 2.82,
		Currency:           "USD",
	}
}

func (rg *ReportGenerator) generateRecommendations(report *MigrationReport) []string {
	var recommendations []string

	if report.Summary.FailedTasks > 0 {
		recommendations = append(recommendations,
			fmt.Sprintf("Review %d failed tasks and retry migration for failed resources", report.Summary.FailedTasks))
	}

	if report.Summary.SuccessRate < 0.8 {
		recommendations = append(recommendations,
			"Success rate below 80%. Recommend running connectivity drill before proceeding")
	}

	recommendations = append(recommendations,
		"Verify migrated resources in target environment",
		"Perform application functionality testing",
		"Schedule cutover during maintenance window",
		"Monitor target environment performance post-migration",
		"Maintain source environment until validation complete")

	return recommendations
}

func (rg *ReportGenerator) ExportReport(report *MigrationReport, format ReportFormat, outputPath string) error {
	var content string
	var err error

	switch format {
	case FormatJSON:
		content, err = rg.exportJSON(report)
	case FormatHTML:
		content, err = rg.exportHTML(report)
	case FormatMarkdown:
		content, err = rg.exportMarkdown(report)
	case FormatText:
		content, err = rg.exportText(report)
	default:
		return fmt.Errorf("unsupported format: %s", format)
	}

	if err != nil {
		return err
	}

	if outputPath != "" {
		dir := filepath.Dir(outputPath)
		if dir != "" {
			if err := os.MkdirAll(dir, 0755); err != nil {
				return fmt.Errorf("failed to create directory: %w", err)
			}
		}
		return os.WriteFile(outputPath, []byte(content), 0644)
	}

	fmt.Println(content)
	return nil
}

func (rg *ReportGenerator) exportJSON(report *MigrationReport) (string, error) {
	data, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		return "", err
	}
	return string(data), nil
}

func (rg *ReportGenerator) exportHTML(report *MigrationReport) (string, error) {
	html := fmt.Sprintf(`<!DOCTYPE html>
<html>
<head>
    <title>Migration Report - %s</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .status-pass { color: green; font-weight: bold; }
        .status-fail { color: red; font-weight: bold; }
        .task { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
        .summary { display: flex; gap: 20px; margin: 20px 0; }
        .summary-box { background: #e8f4f8; padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Cloud Migration Report</h1>
        <p>Report ID: %s</p>
        <p>Generated: %s</p>
        <p>Overall Status: <span class="%s">%s</span></p>
    </div>
    <h2>Migration Details</h2>
    <p><strong>Source:</strong> %s (%s)</p>
    <p><strong>Destination:</strong> %s (%s)</p>
    <h2>Summary</h2>
    <div class="summary">
        <div class="summary-box">
            <h3>Total Tasks</h3>
            <p>%d</p>
        </div>
        <div class="summary-box">
            <h3>Completed</h3>
            <p>%d</p>
        </div>
        <div class="summary-box">
            <h3>Failed</h3>
            <p>%d</p>
        </div>
        <div class="summary-box">
            <h3>Success Rate</h3>
            <p>%.1f%%</p>
        </div>
    </div>
    <h2>Tasks</h2>`,
		report.ReportID,
		report.ReportID,
		report.GeneratedAt.Format(time.RFC3339),
		getStatusClass(report.OverallStatus), report.OverallStatus,
		report.SourceCloud, report.SourceRegion,
		report.DestCloud, report.DestRegion,
		report.Summary.TotalTasks,
		report.Summary.CompletedTasks,
		report.Summary.FailedTasks,
		report.Summary.SuccessRate*100,
	)

	for _, task := range report.Tasks {
		html += fmt.Sprintf(`
    <div class="task">
        <h3>%s (%s)</h3>
        <p>Status: <span class="%s">%s</span></p>
        <p>Progress: %.1f%%</p>
        <p>Duration: %s</p>
        <p>Message: %s</p>
    </div>`,
			task.ResourceName, task.TaskType,
			getStatusClass(task.Status), task.Status,
			task.Progress,
			task.Duration,
			task.Message,
		)
	}

	html += `
    <h2>Recommendations</h2>
    <ul>`
	for _, rec := range report.Recommendations {
		html += fmt.Sprintf("<li>%s</li>", rec)
	}
	html += `
    </ul>
    <h2>Cost Estimate</h2>
    <p>Total Estimated Cost: $%.2f USD</p>
</body>
</html>`, report.CostEstimate.TotalEstimatedCost

	return html, nil
}

func (rg *ReportGenerator) exportMarkdown(report *MigrationReport) (string, error) {
	md := fmt.Sprintf(`# Cloud Migration Report

**Report ID:** %s  
**Generated:** %s  
**Overall Status:** %s

## Migration Details

| | Source | Destination |
|---|---|---|
| Cloud Provider | %s | %s |
| Region | %s | %s |

## Summary

- **Total Tasks:** %d
- **Completed:** %d
- **Failed:** %d
- **Success Rate:** %.1f%%

## Tasks

`,
		report.ReportID,
		report.GeneratedAt.Format(time.RFC3339),
		report.OverallStatus,
		report.SourceCloud, report.DestCloud,
		report.SourceRegion, report.DestRegion,
		report.Summary.TotalTasks,
		report.Summary.CompletedTasks,
		report.Summary.FailedTasks,
		report.Summary.SuccessRate*100,
	)

	for _, task := range report.Tasks {
		md += fmt.Sprintf(`### %s (%s)

- **Status:** %s
- **Progress:** %.1f%%
- **Duration:** %s
- **Message:** %s

`,
			task.ResourceName, task.TaskType,
			task.Status,
			task.Progress,
			task.Duration,
			task.Message,
		)
	}

	md += `## Recommendations

`
	for _, rec := range report.Recommendations {
		md += fmt.Sprintf("- %s\n", rec)
	}

	md += fmt.Sprintf(`

## Cost Estimate

**Total Estimated Cost:** $%.2f USD
`, report.CostEstimate.TotalEstimatedCost)

	return md, nil
}

func (rg *ReportGenerator) exportText(report *MigrationReport) (string, error) {
	text := fmt.Sprintf(`
========================================
     CLOUD MIGRATION REPORT
========================================

Report ID: %s
Generated: %s
Overall Status: %s

MIGRATION DETAILS
-----------------
Source:      %s (%s)
Destination: %s (%s)

SUMMARY
-------
Total Tasks:     %d
Completed:       %d
Failed:          %d
Success Rate:    %.1f%%

TASKS
-----
`,
		report.ReportID,
		report.GeneratedAt.Format(time.RFC3339),
		report.OverallStatus,
		report.SourceCloud, report.SourceRegion,
		report.DestCloud, report.DestRegion,
		report.Summary.TotalTasks,
		report.Summary.CompletedTasks,
		report.Summary.FailedTasks,
		report.Summary.SuccessRate*100,
	)

	for _, task := range report.Tasks {
		text += fmt.Sprintf(`
[%s] %s (%s)
  Progress: %.1f%%
  Duration: %s
  Message: %s
`,
			task.Status,
			task.ResourceName,
			task.TaskType,
			task.Progress,
			task.Duration,
			task.Message,
		)
	}

	text += `
RECOMMENDATIONS
---------------
`
	for _, rec := range report.Recommendations {
		text += fmt.Sprintf("- %s\n", rec)
	}

	text += fmt.Sprintf(`
COST ESTIMATE
-------------
Total Estimated Cost: $%.2f USD

========================================
`, report.CostEstimate.TotalEstimatedCost)

	return text, nil
}

func getStatusClass(status string) string {
	switch status {
	case "completed", "passed":
		return "status-pass"
	case "failed":
		return "status-fail"
	default:
		return ""
	}
}
