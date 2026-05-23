package history

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"
)

type ScalingAction string

const (
	ActionScaleUp   ScalingAction = "scale_up"
	ActionScaleDown ScalingAction = "scale_down"
	ActionNoChange  ScalingAction = "no_change"
)

type ScalingReason string

const (
	ReasonHighCPU        ScalingReason = "high_cpu"
	ReasonHighMemory     ScalingReason = "high_memory"
	ReasonLowCPU         ScalingReason = "low_cpu"
	ReasonLowMemory      ScalingReason = "low_memory"
	ReasonPredictedLoad  ScalingReason = "predicted_load"
	ReasonCostOptimization ScalingReason = "cost_optimization"
	ReasonCooldown       ScalingReason = "in_cooldown"
	ReasonMinInstances   ScalingReason = "min_instances_limit"
	ReasonMaxInstances   ScalingReason = "max_instances_limit"
)

type ScalingRecord struct {
	ID              string        `json:"id"`
	Timestamp       time.Time     `json:"timestamp"`
	InstanceGroup   string        `json:"instance_group"`
	Action          ScalingAction `json:"action"`
	InstanceCount   int           `json:"instance_count"`
	InstancesBefore int           `json:"instances_before"`
	InstancesAfter  int           `json:"instances_after"`
	Reason          ScalingReason `json:"reason"`
	ReasonDetail    string        `json:"reason_detail"`
	CPUUtilization  float64       `json:"cpu_utilization"`
	MemoryUtilization float64     `json:"memory_utilization"`
	PredictedCPU    float64       `json:"predicted_cpu,omitempty"`
	PredictedMemory float64       `json:"predicted_memory,omitempty"`
	CostChange      float64       `json:"cost_change"`
	CostBefore      float64       `json:"cost_before"`
	CostAfter       float64       `json:"cost_after"`
	Status          string        `json:"status"`
	ErrorMessage    string        `json:"error_message,omitempty"`
	DurationMs      int64         `json:"duration_ms"`
}

type HistoryStore struct {
	records     []ScalingRecord
	maxRecords  int
	filePath    string
	mu          sync.RWMutex
}

func NewHistoryStore(filePath string, maxRecords int) *HistoryStore {
	store := &HistoryStore{
		records:    make([]ScalingRecord, 0, maxRecords),
		maxRecords: maxRecords,
		filePath:   filePath,
	}
	store.load()
	return store
}

func (s *HistoryStore) AddRecord(record ScalingRecord) {
	s.mu.Lock()
	defer s.mu.Unlock()

	if record.ID == "" {
		record.ID = generateID()
	}
	record.Timestamp = time.Now()

	s.records = append(s.records, record)
	if len(s.records) > s.maxRecords {
		s.records = s.records[1:]
	}

	s.save()
}

func (s *HistoryStore) GetAll() []ScalingRecord {
	s.mu.RLock()
	defer s.mu.RUnlock()
	records := make([]ScalingRecord, len(s.records))
	copy(records, s.records)
	return records
}

func (s *HistoryStore) GetByTimeRange(start, end time.Time) []ScalingRecord {
	s.mu.RLock()
	defer s.mu.RUnlock()

	var result []ScalingRecord
	for _, r := range s.records {
		if r.Timestamp.After(start) && r.Timestamp.Before(end) {
			result = append(result, r)
		}
	}
	return result
}

func (s *HistoryStore) GetLatest(n int) []ScalingRecord {
	s.mu.RLock()
	defer s.mu.RUnlock()

	if n > len(s.records) {
		n = len(s.records)
	}
	result := make([]ScalingRecord, n)
	copy(result, s.records[len(s.records)-n:])
	return result
}

func (s *HistoryStore) load() {
	if s.filePath == "" {
		return
	}

	data, err := os.ReadFile(s.filePath)
	if err != nil {
		if os.IsNotExist(err) {
			return
		}
		fmt.Printf("Warning: failed to load history: %v\n", err)
		return
	}

	var records []ScalingRecord
	if err := json.Unmarshal(data, &records); err != nil {
		fmt.Printf("Warning: failed to parse history: %v\n", err)
		return
	}

	s.records = records
}

func (s *HistoryStore) save() {
	if s.filePath == "" {
		return
	}

	dir := filepath.Dir(s.filePath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		fmt.Printf("Warning: failed to create directory: %v\n", err)
		return
	}

	data, err := json.MarshalIndent(s.records, "", "  ")
	if err != nil {
		fmt.Printf("Warning: failed to marshal history: %v\n", err)
		return
	}

	if err := os.WriteFile(s.filePath, data, 0644); err != nil {
		fmt.Printf("Warning: failed to save history: %v\n", err)
	}
}

func generateID() string {
	return fmt.Sprintf("scale-%d", time.Now().UnixNano())
}

type ReportSummary struct {
	TotalActions      int     `json:"total_actions"`
	ScaleUpCount      int     `json:"scale_up_count"`
	ScaleDownCount    int     `json:"scale_down_count"`
	TotalCostChange   float64 `json:"total_cost_change"`
	SuccessRate       float64 `json:"success_rate"`
	AvgScaleUpTime    float64 `json:"avg_scale_up_time_ms"`
	AvgScaleDownTime  float64 `json:"avg_scale_down_time_ms"`
}

func (s *HistoryStore) GenerateReport(start, end time.Time) (*ReportSummary, []ScalingRecord) {
	records := s.GetByTimeRange(start, end)
	if len(records) == 0 {
		return &ReportSummary{}, records
	}

	summary := &ReportSummary{
		TotalActions: len(records),
	}

	var successCount int
	var scaleUpTime, scaleDownTime float64
	var scaleUpCount, scaleDownCount int

	for _, r := range records {
		summary.TotalCostChange += r.CostChange

		switch r.Action {
		case ActionScaleUp:
			summary.ScaleUpCount++
			scaleUpCount++
			scaleUpTime += float64(r.DurationMs)
		case ActionScaleDown:
			summary.ScaleDownCount++
			scaleDownCount++
			scaleDownTime += float64(r.DurationMs)
		}

		if r.Status == "success" {
			successCount++
		}
	}

	summary.SuccessRate = float64(successCount) / float64(len(records)) * 100
	if scaleUpCount > 0 {
		summary.AvgScaleUpTime = scaleUpTime / float64(scaleUpCount)
	}
	if scaleDownCount > 0 {
		summary.AvgScaleDownTime = scaleDownTime / float64(scaleDownCount)
	}

	sort.Slice(records, func(i, j int) bool {
		return records[i].Timestamp.After(records[j].Timestamp)
	})

	return summary, records
}

func (s *HistoryStore) GenerateHTMLReport(start, end time.Time) string {
	summary, records := s.GenerateReport(start, end)

	html := `
<!DOCTYPE html>
<html>
<head>
    <title>Scaling History Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .summary-item { display: inline-block; margin-right: 30px; }
        .summary-value { font-size: 24px; font-weight: bold; color: #2c3e50; }
        .summary-label { font-size: 12px; color: #7f8c8d; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #34495e; color: white; }
        tr:hover { background: #f9f9f9; }
        .scale-up { color: #27ae60; font-weight: bold; }
        .scale-down { color: #e74c3c; font-weight: bold; }
        .success { color: #27ae60; }
        .failed { color: #e74c3c; }
    </style>
</head>
<body>
    <h1>Scaling History Report</h1>
    <p>` + start.Format("2006-01-02 15:04:05") + ` to ` + end.Format("2006-01-02 15:04:05") + `</p>
    
    <div class="summary">
        <div class="summary-item">
            <div class="summary-value">` + fmt.Sprintf("%d", summary.TotalActions) + `</div>
            <div class="summary-label">Total Actions</div>
        </div>
        <div class="summary-item">
            <div class="summary-value scale-up">` + fmt.Sprintf("%d", summary.ScaleUpCount) + `</div>
            <div class="summary-label">Scale Ups</div>
        </div>
        <div class="summary-item">
            <div class="summary-value scale-down">` + fmt.Sprintf("%d", summary.ScaleDownCount) + `</div>
            <div class="summary-label">Scale Downs</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">$` + fmt.Sprintf("%.2f", summary.TotalCostChange) + `</div>
            <div class="summary-label">Total Cost Change</div>
        </div>
        <div class="summary-item">
            <div class="summary-value">` + fmt.Sprintf("%.1f%%", summary.SuccessRate) + `</div>
            <div class="summary-label">Success Rate</div>
        </div>
    </div>

    <h2>Scaling Events</h2>
    <table>
        <tr>
            <th>Time</th>
            <th>Action</th>
            <th>Instances</th>
            <th>Reason</th>
            <th>CPU/Memory</th>
            <th>Cost Change</th>
            <th>Status</th>
        </tr>
`

	for _, r := range records {
		actionClass := ""
		if r.Action == ActionScaleUp {
			actionClass = "scale-up"
		} else if r.Action == ActionScaleDown {
			actionClass = "scale-down"
		}

		statusClass := "success"
		if r.Status != "success" {
			statusClass = "failed"
		}

		html += `
        <tr>
            <td>` + r.Timestamp.Format("2006-01-02 15:04:05") + `</td>
            <td class="` + actionClass + `">` + string(r.Action) + `</td>
            <td>` + fmt.Sprintf("%d → %d", r.InstancesBefore, r.InstancesAfter) + `</td>
            <td>` + string(r.Reason) + `</td>
            <td>` + fmt.Sprintf("%.1f%% / %.1f%%", r.CPUUtilization, r.MemoryUtilization) + `</td>
            <td>$` + fmt.Sprintf("%.2f", r.CostChange) + `</td>
            <td class="` + statusClass + `">` + r.Status + `</td>
        </tr>
`
	}

	html += `
    </table>
</body>
</html>
`

	return html
}
