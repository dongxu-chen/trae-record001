package audit

import (
	"encoding/json"
	"os"
	"sync"
	"time"
)

type AuditAction string

const (
	ActionTagAdded    AuditAction = "tag_added"
	ActionTagModified AuditAction = "tag_modified"
	ActionTagDeleted  AuditAction = "tag_deleted"
	ActionTagsApplied AuditAction = "tags_applied"
	ActionBulkUpdate  AuditAction = "bulk_update"
)

type TagChange struct {
	Key      string `json:"key"`
	OldValue string `json:"oldValue,omitempty"`
	NewValue string `json:"newValue,omitempty"`
}

type AuditLogEntry struct {
	ID           string                 `json:"id"`
	Timestamp    string                 `json:"timestamp"`
	ResourceID   string                 `json:"resourceId"`
	ResourceName string                 `json:"resourceName"`
	ResourceType string                 `json:"resourceType"`
	AccountID    string                 `json:"accountId"`
	AccountName  string                 `json:"accountName"`
	Action       AuditAction            `json:"action"`
	Changes      []TagChange            `json:"changes"`
	Operator     string                 `json:"operator"`
	OperatorRole string                 `json:"operatorRole"`
	Source       string                 `json:"source"`
	Description  string                 `json:"description"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
}

type AuditLogger struct {
	mu        sync.RWMutex
	logs      []AuditLogEntry
	logFile   string
	autoSave  bool
}

func NewAuditLogger(logFile string) *AuditLogger {
	logger := &AuditLogger{
		logs:     make([]AuditLogEntry, 0),
		logFile:  logFile,
		autoSave: true,
	}
	logger.load()
	return logger
}

func (l *AuditLogger) load() {
	if l.logFile == "" {
		return
	}

	data, err := os.ReadFile(l.logFile)
	if err != nil {
		return
	}

	var logs []AuditLogEntry
	if err := json.Unmarshal(data, &logs); err == nil {
		l.logs = logs
	}
}

func (l *AuditLogger) save() {
	if !l.autoSave || l.logFile == "" {
		return
	}

	l.mu.RLock()
	defer l.mu.RUnlock()

	data, err := json.MarshalIndent(l.logs, "", "  ")
	if err != nil {
		return
	}

	os.WriteFile(l.logFile, data, 0644)
}

func (l *AuditLogger) Log(entry AuditLogEntry) {
	l.mu.Lock()
	defer l.mu.Unlock()

	entry.ID = generateLogID()
	entry.Timestamp = time.Now().Format(time.RFC3339)

	l.logs = append([]AuditLogEntry{entry}, l.logs...)

	go l.save()
}

func (l *AuditLogger) LogTagChange(
	resourceID, resourceName, resourceType string,
	accountID, accountName string,
	action AuditAction,
	changes []TagChange,
	operator, operatorRole, source string,
) {
	description := generateDescription(action, changes)

	l.Log(AuditLogEntry{
		ResourceID:   resourceID,
		ResourceName: resourceName,
		ResourceType: resourceType,
		AccountID:    accountID,
		AccountName:  accountName,
		Action:       action,
		Changes:      changes,
		Operator:     operator,
		OperatorRole: operatorRole,
		Source:       source,
		Description:  description,
	})
}

func generateDescription(action AuditAction, changes []TagChange) string {
	switch action {
	case ActionTagAdded:
		if len(changes) > 0 {
			return "添加标签: " + changes[0].Key
		}
	case ActionTagModified:
		if len(changes) > 0 {
			return "修改标签: " + changes[0].Key
		}
	case ActionTagDeleted:
		if len(changes) > 0 {
			return "删除标签: " + changes[0].Key
		}
	case ActionTagsApplied:
		return "批量应用标签模板"
	case ActionBulkUpdate:
		return "批量更新标签: " + string(len(changes)) + " 个标签"
	}
	return string(action)
}

func generateLogID() string {
	return "audit-" + time.Now().Format("20060102150405") + "-" + randomString(6)
}

func randomString(n int) string {
	const charset = "abcdefghijklmnopqrstuvwxyz0123456789"
	b := make([]byte, n)
	for i := range b {
		b[i] = charset[time.Now().UnixNano()%int64(len(charset))]
		time.Sleep(time.Nanosecond)
	}
	return string(b)
}

func (l *AuditLogger) Query(resourceID, action, operator, startDate, endDate string, limit int) []AuditLogEntry {
	l.mu.RLock()
	defer l.mu.RUnlock()

	var results []AuditLogEntry

	for _, entry := range l.logs {
		if resourceID != "" && entry.ResourceID != resourceID {
			continue
		}
		if action != "" && string(entry.Action) != action {
			continue
		}
		if operator != "" && entry.Operator != operator {
			continue
		}
		if startDate != "" && entry.Timestamp < startDate {
			continue
		}
		if endDate != "" && entry.Timestamp > endDate {
			continue
		}

		results = append(results, entry)
		if limit > 0 && len(results) >= limit {
			break
		}
	}

	return results
}

func (l *AuditLogger) GetAll() []AuditLogEntry {
	l.mu.RLock()
	defer l.mu.RUnlock()

	logs := make([]AuditLogEntry, len(l.logs))
	copy(logs, l.logs)
	return logs
}

func (l *AuditLogger) GetByResource(resourceID string) []AuditLogEntry {
	return l.Query(resourceID, "", "", "", "", 0)
}

func (l *AuditLogger) GetByOperator(operator string) []AuditLogEntry {
	return l.Query("", "", operator, "", "", 0)
}

func (l *AuditLogger) GetByAction(action AuditAction) []AuditLogEntry {
	return l.Query("", string(action), "", "", "", 0)
}

func (l *AuditLogger) GetByDateRange(startDate, endDate string) []AuditLogEntry {
	return l.Query("", "", "", startDate, endDate, 0)
}

func (l *AuditLogger) GetStatistics() map[string]interface{} {
	l.mu.RLock()
	defer l.mu.RUnlock()

	stats := map[string]interface{}{
		"totalLogs":       len(l.logs),
		"byAction":        make(map[string]int),
		"byOperator":      make(map[string]int),
		"byResourceType":  make(map[string]int),
		"todayCount":      0,
		"thisWeekCount":   0,
	}

	today := time.Now().Format("2006-01-02")
	weekAgo := time.Now().AddDate(0, 0, -7).Format("2006-01-02")

	for _, entry := range l.logs {
		stats["byAction"].(map[string]int)[string(entry.Action)]++
		stats["byOperator"].(map[string]int)[entry.Operator]++
		stats["byResourceType"].(map[string]int)[entry.ResourceType]++

		entryDate := entry.Timestamp[:10]
		if entryDate == today {
			stats["todayCount"] = stats["todayCount"].(int) + 1
		}
		if entryDate >= weekAgo {
			stats["thisWeekCount"] = stats["thisWeekCount"].(int) + 1
		}
	}

	return stats
}

func (l *AuditLogger) GetTagHistory(resourceID, tagKey string) []TagChange {
	logs := l.GetByResource(resourceID)
	var history []TagChange

	for _, entry := range logs {
		for _, change := range entry.Changes {
			if change.Key == tagKey {
				history = append(history, change)
			}
		}
	}

	return history
}

func (l *AuditLogger) RevertToVersion(resourceID string, logID string) (bool, string) {
	l.mu.Lock()
	defer l.mu.Unlock()

	for i, entry := range l.logs {
		if entry.ID == logID {
			if i+1 < len(l.logs) {
				return true, "已定位到历史版本，可执行回滚"
			}
			return false, "已是最新版本"
		}
	}

	return false, "未找到指定的审计日志"
}

func (l *AuditLogger) Export(startDate, endDate string) ([]byte, error) {
	logs := l.GetByDateRange(startDate, endDate)
	return json.MarshalIndent(map[string]interface{}{
		"exportDate":  time.Now().Format(time.RFC3339),
		"dateRange":   map[string]string{"start": startDate, "end": endDate},
		"totalCount":  len(logs),
		"auditLogs":   logs,
	}, "", "  ")
}
