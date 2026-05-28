package audit

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"

	corev1 "k8s.io/api/core/v1"

	"container-autoscaler/pkg/config"
	"container-autoscaler/pkg/types"
	"container-autoscaler/pkg/utils"
)

type Auditor struct {
	config     config.AuditConfig
	logger     *utils.Logger
	records    []types.AuditRecord
	recordLock sync.RWMutex
	logFile    *os.File
}

func NewAuditor(cfg config.AuditConfig, logger *utils.Logger) (*Auditor, error) {
	auditor := &Auditor{
		config:  cfg,
		logger:  logger,
		records: make([]types.AuditRecord, 0),
	}

	if cfg.Enabled && cfg.LogPath != "" {
		if err := os.MkdirAll(filepath.Dir(cfg.LogPath), 0755); err != nil {
			return nil, fmt.Errorf("creating audit log directory: %w", err)
		}

		f, err := os.OpenFile(cfg.LogPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if err != nil {
			return nil, fmt.Errorf("opening audit log file: %w", err)
		}
		auditor.logFile = f
	}

	return auditor, nil
}

func (a *Auditor) Close() error {
	if a.logFile != nil {
		return a.logFile.Close()
	}
	return nil
}

func (a *Auditor) RecordAdjustment(
	ctx context.Context,
	namespace string,
	podName string,
	containerName string,
	nodeName string,
	resourceType corev1.ResourceName,
	beforeLimit float64,
	beforeRequest float64,
	beforeUsage float64,
	afterLimit float64,
	afterRequest float64,
	reason string,
	confidence float64,
	dryRun bool,
	success bool,
	errMsg string,
) string {
	record := types.AuditRecord{
		ID:            generateID(),
		Timestamp:     time.Now(),
		Namespace:     namespace,
		PodName:       podName,
		ContainerName: containerName,
		NodeName:      nodeName,
		ResourceType:  resourceType,
		Before: types.ResourceState{
			Limit:    beforeLimit,
			Request:  beforeRequest,
			Usage:    beforeUsage,
			UsagePct: beforeUsage / beforeLimit * 100,
		},
		After: types.ResourceState{
			Limit:    afterLimit,
			Request:  afterRequest,
			Usage:    beforeUsage,
			UsagePct: beforeUsage / afterLimit * 100,
		},
		Reason:     reason,
		Confidence: confidence,
		DryRun:     dryRun,
		Success:    success,
		ErrorMessage: errMsg,
	}

	record.PerformanceDiff = a.calculatePerformanceDiff(record)

	a.recordLock.Lock()
	a.records = append(a.records, record)
	a.recordLock.Unlock()

	if a.logFile != nil {
		recordJSON, _ := json.Marshal(record)
		if _, err := a.logFile.WriteString(string(recordJSON) + "\n"); err != nil {
			a.logger.Warning("Failed to write audit record: %v", err)
		}
	}

	a.logger.Info("[AUDIT] %s/%s/%s %s: %.0f -> %.0f (confidence: %.2f, success: %t)",
		namespace, podName, containerName, resourceType,
		beforeLimit, afterLimit, confidence, success)

	return record.ID
}

func (a *Auditor) calculatePerformanceDiff(record types.AuditRecord) types.PerformanceMetrics {
	utilizationChange := record.After.UsagePct - record.Before.UsagePct

	beforeWaste := record.Before.Limit - record.Before.Usage
	afterWaste := record.After.Limit - record.Before.Usage
	wasteChange := afterWaste - beforeWaste

	beforeEfficiency := 0.0
	if record.Before.Limit > 0 {
		beforeEfficiency = record.Before.Usage / record.Before.Limit
	}
	afterEfficiency := 0.0
	if record.After.Limit > 0 {
		afterEfficiency = record.After.Usage / record.After.Limit
	}
	efficiencyChange := afterEfficiency - beforeEfficiency

	contentionChange := 0.0
	if record.After.UsagePct > 95 {
		contentionChange = (record.After.UsagePct - 95) / 100
	}

	return types.PerformanceMetrics{
		UtilizationChange:  utilizationChange,
		EfficiencyChange:   efficiencyChange,
		WasteChange:        wasteChange,
		ContentionRiskChange: contentionChange,
	}
}

func (a *Auditor) GetRecords(namespace, podName, containerName string, limit int) []types.AuditRecord {
	a.recordLock.RLock()
	defer a.recordLock.RUnlock()

	result := make([]types.AuditRecord, 0, limit)

	for i := len(a.records) - 1; i >= 0 && len(result) < limit; i-- {
		rec := a.records[i]
		match := true

		if namespace != "" && rec.Namespace != namespace {
			match = false
		}
		if podName != "" && rec.PodName != podName {
			match = false
		}
		if containerName != "" && rec.ContainerName != containerName {
			match = false
		}

		if match {
			result = append(result, rec)
		}
	}

	return result
}

func (a *Auditor) GenerateReport(startTime, endTime time.Time) *AuditReport {
	a.recordLock.RLock()
	defer a.recordLock.RUnlock()

	report := &AuditReport{
		StartTime:      startTime,
		EndTime:        endTime,
		TotalAdjustments: 0,
		Successful:     0,
		Failed:         0,
		DryRuns:        0,
		ByResourceType: make(map[string]ResourceSummary),
		ByNamespace:    make(map[string]int),
	}

	filtered := make([]types.AuditRecord, 0)
	for _, rec := range a.records {
		if rec.Timestamp.After(startTime) && rec.Timestamp.Before(endTime) {
			filtered = append(filtered, rec)
		}
	}

	sort.Slice(filtered, func(i, j int) bool {
		return filtered[i].Timestamp.Before(filtered[j].Timestamp)
	})

	for _, rec := range filtered {
		report.TotalAdjustments++

		if rec.DryRun {
			report.DryRuns++
		} else if rec.Success {
			report.Successful++
		} else {
			report.Failed++
		}

		rt := string(rec.ResourceType)
		rs, ok := report.ByResourceType[rt]
		if !ok {
			rs = ResourceSummary{}
		}
		rs.Count++
		rs.TotalLimitIncrease += rec.After.Limit - rec.Before.Limit
		rs.TotalWasteSaved += rec.PerformanceDiff.WasteChange
		rs.AvgEfficiencyChange += rec.PerformanceDiff.EfficiencyChange
		report.ByResourceType[rt] = rs

		report.ByNamespace[rec.Namespace]++
		report.TotalWasteSaved += rec.PerformanceDiff.WasteChange
	}

	for rt, rs := range report.ByResourceType {
		if rs.Count > 0 {
			rs.AvgEfficiencyChange /= float64(rs.Count)
			report.ByResourceType[rt] = rs
		}
	}

	report.Adjustments = filtered
	return report
}

type AuditReport struct {
	StartTime        time.Time
	EndTime          time.Time
	TotalAdjustments int
	Successful       int
	Failed           int
	DryRuns          int
	TotalWasteSaved  float64
	ByResourceType   map[string]ResourceSummary
	ByNamespace      map[string]int
	Adjustments      []types.AuditRecord
}

type ResourceSummary struct {
	Count                int
	TotalLimitIncrease   float64
	TotalWasteSaved      float64
	AvgEfficiencyChange  float64
}

func (a *Auditor) PrintReport(report *AuditReport) {
	a.logger.Info("========================================")
	a.logger.Info("        AUDIT REPORT SUMMARY")
	a.logger.Info("========================================")
	a.logger.Info("Period: %s to %s", report.StartTime.Format(time.RFC3339), report.EndTime.Format(time.RFC3339))
	a.logger.Info("Total Adjustments: %d", report.TotalAdjustments)
	a.logger.Info("  - Successful: %d", report.Successful)
	a.logger.Info("  - Failed: %d", report.Failed)
	a.logger.Info("  - Dry Runs: %d", report.DryRuns)
	a.logger.Info("Total Waste Saved: %.0f units", report.TotalWasteSaved)
	a.logger.Info("")
	a.logger.Info("By Resource Type:")
	for rt, rs := range report.ByResourceType {
		a.logger.Info("  %s:", rt)
		a.logger.Info("    Count: %d", rs.Count)
		a.logger.Info("    Avg Efficiency Change: %.2f%%", rs.AvgEfficiencyChange*100)
		a.logger.Info("    Total Waste Saved: %.0f", rs.TotalWasteSaved)
	}
	a.logger.Info("")
	a.logger.Info("By Namespace:")
	for ns, count := range report.ByNamespace {
		a.logger.Info("  %s: %d adjustments", ns, count)
	}
	a.logger.Info("========================================")
}

func (a *Auditor) CleanupOldRecords() error {
	if a.config.RetentionDays <= 0 {
		return nil
	}

	cutoff := time.Now().AddDate(0, 0, -a.config.RetentionDays)

	a.recordLock.Lock()
	defer a.recordLock.Unlock()

	kept := make([]types.AuditRecord, 0)
	removed := 0

	for _, rec := range a.records {
		if rec.Timestamp.After(cutoff) {
			kept = append(kept, rec)
		} else {
			removed++
		}
	}

	a.records = kept
	if removed > 0 {
		a.logger.Debug("Cleaned up %d old audit records (retention: %d days)", removed, a.config.RetentionDays)
	}

	return nil
}

func (a *Auditor) GetLatestAdjustment(namespace, podName, containerName string, resourceType corev1.ResourceName) *types.AuditRecord {
	a.recordLock.RLock()
	defer a.recordLock.RUnlock()

	for i := len(a.records) - 1; i >= 0; i-- {
		rec := a.records[i]
		if rec.Namespace == namespace &&
			rec.PodName == podName &&
			rec.ContainerName == containerName &&
			rec.ResourceType == resourceType {
			return &rec
		}
	}

	return nil
}

func generateID() string {
	return fmt.Sprintf("adj-%d", time.Now().UnixNano())
}
