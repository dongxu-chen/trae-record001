package auditor

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

type AuditAction string

const (
	ActionKillInitiated  AuditAction = "KILL_INITIATED"
	ActionKillCompleted  AuditAction = "KILL_COMPLETED"
	ActionKillFailed     AuditAction = "KILL_FAILED"
	ActionWaitStarted    AuditAction = "WAIT_STARTED"
	ActionWaitCompleted  AuditAction = "WAIT_COMPLETED"
	ActionWaitTimeout    AuditAction = "WAIT_TIMEOUT"
	ActionQueryWhitelisted AuditAction = "QUERY_WHITELISTED"
	ActionRuleMatched    AuditAction = "RULE_MATCHED"
	ActionPredictionHigh AuditAction = "PREDICTION_HIGH_RISK"
)

type ImpactAssessment struct {
	TransactionRisk    string  `json:"transaction_risk"`
	RollbackProbability float64 `json:"rollback_probability"`
	BusinessImpact     string  `json:"business_impact"`
	RecommendedAction  string  `json:"recommended_action"`
	Alternative        string  `json:"alternative,omitempty"`
}

type AuditLog struct {
	Timestamp     time.Time         `json:"timestamp"`
	Action        AuditAction       `json:"action"`
	DBName        string            `json:"db_name"`
	ConnectionID  int64             `json:"connection_id"`
	User          string            `json:"user"`
	Host          string            `json:"host"`
	QueryHash     string            `json:"query_hash"`
	QuerySample   string            `json:"query_sample"`
	ExecutionTime time.Duration     `json:"execution_time"`
	RuleName      string            `json:"rule_name,omitempty"`
	KillMode      string            `json:"kill_mode,omitempty"`
	WaitDuration  time.Duration     `json:"wait_duration,omitempty"`
	Impact        *ImpactAssessment `json:"impact_assessment,omitempty"`
	Error         string            `json:"error,omitempty"`
	Operator      string            `json:"operator"`
}

type Auditor struct {
	logFile     *os.File
	logPath     string
	jsonEncoder *json.Encoder
	buffer      []AuditLog
	bufferSize  int
	mu          sync.Mutex
	rotateDaily bool
}

type AuditSummary struct {
	TotalKills        int            `json:"total_kills"`
	TotalWaitStarts   int            `json:"total_wait_starts"`
	TotalWaitCompletes int           `json:"total_wait_completes"`
	TotalWaitTimeouts int            `json:"total_wait_timeouts"`
	TotalWhitelisted  int            `json:"total_whitelisted"`
	KillByUser        map[string]int `json:"kills_by_user"`
	KillByDB          map[string]int `json:"kills_by_db"`
	KillByRule        map[string]int `json:"kills_by_rule"`
	AvgWaitTime       time.Duration  `json:"average_wait_time"`
	PeriodStart       time.Time      `json:"period_start"`
	PeriodEnd         time.Time      `json:"period_end"`
}

func NewAuditor(logPath string, rotateDaily bool) (*Auditor, error) {
	dir := filepath.Dir(logPath)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create log directory: %w", err)
	}

	file, err := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return nil, fmt.Errorf("failed to open audit log file: %w", err)
	}

	return &Auditor{
		logFile:     file,
		logPath:     logPath,
		jsonEncoder: json.NewEncoder(file),
		bufferSize:  100,
		rotateDaily: rotateDaily,
	}, nil
}

func (a *Auditor) Close() error {
	a.mu.Lock()
	defer a.mu.Unlock()

	if len(a.buffer) > 0 {
		a.flushBuffer()
	}

	if a.logFile != nil {
		return a.logFile.Close()
	}
	return nil
}

func (a *Auditor) Record(action AuditAction, log AuditLog) {
	log.Timestamp = time.Now()
	log.Action = action
	log.Operator = "system"

	a.mu.Lock()
	defer a.mu.Unlock()

	a.buffer = append(a.buffer, log)

	if len(a.buffer) >= a.bufferSize {
		a.flushBuffer()
	}
}

func (a *Auditor) RecordKill(dbName string, connID int64, user, host string,
	queryHash, querySample string, execTime time.Duration, ruleName, killMode string,
	waitDuration time.Duration, err error) {

	action := ActionKillCompleted
	errMsg := ""
	if err != nil {
		action = ActionKillFailed
		errMsg = err.Error()
	}

	impact := assessImpact(querySample, execTime, killMode)

	a.Record(action, AuditLog{
		DBName:        dbName,
		ConnectionID:  connID,
		User:          user,
		Host:          host,
		QueryHash:     queryHash,
		QuerySample:   truncateQuery(querySample, 500),
		ExecutionTime: execTime,
		RuleName:      ruleName,
		KillMode:      killMode,
		WaitDuration:  waitDuration,
		Impact:        impact,
		Error:         errMsg,
	})
}

func (a *Auditor) RecordWait(dbName string, connID int64, user, host string,
	queryHash, querySample string, execTime time.Duration, completed bool, waitDuration time.Duration) {

	action := ActionWaitTimeout
	if completed {
		action = ActionWaitCompleted
	}

	a.Record(action, AuditLog{
		DBName:        dbName,
		ConnectionID:  connID,
		User:          user,
		Host:          host,
		QueryHash:     queryHash,
		QuerySample:   truncateQuery(querySample, 500),
		ExecutionTime: execTime,
		WaitDuration:  waitDuration,
	})
}

func (a *Auditor) RecordWhitelist(queryHash, querySample string, reason string) {
	a.Record(ActionQueryWhitelisted, AuditLog{
		QueryHash:   queryHash,
		QuerySample: truncateQuery(querySample, 500),
		RuleName:    reason,
	})
}

func (a *Auditor) flushBuffer() {
	for _, log := range a.buffer {
		_ = a.jsonEncoder.Encode(log)
	}
	a.buffer = a.buffer[:0]
	a.logFile.Sync()
}

func assessImpact(querySample string, execTime time.Duration, killMode string) *ImpactAssessment {
	upper := strings.ToUpper(querySample)

	isWrite := strings.Contains(upper, "INSERT") ||
		strings.Contains(upper, "UPDATE") ||
		strings.Contains(upper, "DELETE")

	isTransaction := strings.Contains(upper, "BEGIN") ||
		strings.Contains(upper, "COMMIT") ||
		strings.Contains(upper, "ROLLBACK") ||
		strings.Contains(upper, "TRANSACTION")

	impact := &ImpactAssessment{
		TransactionRisk:    "LOW",
		RollbackProbability: 0.1,
		BusinessImpact:     "MINIMAL",
		RecommendedAction:  "MONITOR",
	}

	if isWrite || isTransaction {
		impact.TransactionRisk = "HIGH"
		impact.RollbackProbability = 0.8
		impact.BusinessImpact = "MODERATE"
		impact.RecommendedAction = "CONSIDER_WAIT"
		impact.Alternative = "Enable transaction wait before kill"
	}

	if execTime > 5*time.Minute {
		impact.BusinessImpact = "HIGH"
		impact.RecommendedAction = "KILL_IMMEDIATELY"
	} else if execTime > 1*time.Minute {
		impact.BusinessImpact = "MODERATE"
	}

	if killMode == "connection" && (isWrite || isTransaction) {
		impact.RollbackProbability = 1.0
		impact.Alternative = "Use query-level kill instead of connection kill"
	}

	return impact
}

func (a *Auditor) GenerateSummary(startTime, endTime time.Time) (*AuditSummary, error) {
	summary := &AuditSummary{
		KillByUser:  make(map[string]int),
		KillByDB:    make(map[string]int),
		KillByRule:  make(map[string]int),
		PeriodStart: startTime,
		PeriodEnd:   endTime,
	}

	file, err := os.Open(a.logPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	decoder := json.NewDecoder(file)
	totalWaitTime := time.Duration(0)
	waitCount := 0

	for {
		var log AuditLog
		if err := decoder.Decode(&log); err != nil {
			break
		}

		if log.Timestamp.Before(startTime) || log.Timestamp.After(endTime) {
			continue
		}

		switch log.Action {
		case ActionKillCompleted:
			summary.TotalKills++
			summary.KillByUser[log.User]++
			summary.KillByDB[log.DBName]++
			if log.RuleName != "" {
				summary.KillByRule[log.RuleName]++
			}
		case ActionWaitStarted:
			summary.TotalWaitStarts++
		case ActionWaitCompleted:
			summary.TotalWaitCompletes++
			totalWaitTime += log.WaitDuration
			waitCount++
		case ActionWaitTimeout:
			summary.TotalWaitTimeouts++
			totalWaitTime += log.WaitDuration
			waitCount++
		case ActionQueryWhitelisted:
			summary.TotalWhitelisted++
		}
	}

	if waitCount > 0 {
		summary.AvgWaitTime = totalWaitTime / time.Duration(waitCount)
	}

	return summary, nil
}

func (a *Auditor) Flush() {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.flushBuffer()
}

func (a *Auditor) GenerateImpactReport() string {
	summary, err := a.GenerateSummary(time.Now().Add(-24*time.Hour), time.Now())
	if err != nil {
		return fmt.Sprintf("Error generating audit summary: %v", err)
	}

	var report strings.Builder
	report.WriteString("\n=== Audit Log Impact Report (Last 24h) ===\n")
	report.WriteString(fmt.Sprintf("Period: %s to %s\n\n",
		summary.PeriodStart.Format(time.RFC3339),
		summary.PeriodEnd.Format(time.RFC3339)))

	report.WriteString(fmt.Sprintf("Total queries killed: %d\n", summary.TotalKills))
	report.WriteString(fmt.Sprintf("Transaction waits started: %d\n", summary.TotalWaitStarts))
	report.WriteString(fmt.Sprintf("Transaction waits completed: %d\n", summary.TotalWaitCompletes))
	report.WriteString(fmt.Sprintf("Transaction waits timed out: %d\n", summary.TotalWaitTimeouts))
	report.WriteString(fmt.Sprintf("Average wait time: %v\n", summary.AvgWaitTime))
	report.WriteString(fmt.Sprintf("Queries whitelisted: %d\n\n", summary.TotalWhitelisted))

	if len(summary.KillByRule) > 0 {
		report.WriteString("Kills by Rule:\n")
		for rule, count := range summary.KillByRule {
			report.WriteString(fmt.Sprintf("  - %s: %d\n", rule, count))
		}
		report.WriteString("\n")
	}

	if len(summary.KillByDB) > 0 {
		report.WriteString("Kills by Database:\n")
		for db, count := range summary.KillByDB {
			report.WriteString(fmt.Sprintf("  - %s: %d\n", db, count))
		}
	}

	return report.String()
}

func truncateQuery(query string, maxLen int) string {
	if len(query) <= maxLen {
		return query
	}
	return query[:maxLen] + "..."
}
