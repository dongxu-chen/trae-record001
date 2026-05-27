package audit

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sync"
	"time"
)

type ActionType string

const (
	ActionSync    ActionType = "SYNC"
	ActionSkip    ActionType = "SKIP"
	ActionDelete  ActionType = "DELETE"
	ActionPush    ActionType = "PUSH"
	ActionPull    ActionType = "PULL"
	ActionVerify  ActionType = "VERIFY"
	ActionRelay   ActionType = "RELAY"
)

type AuditEntry struct {
	ID           string            `json:"id"`
	Timestamp    time.Time         `json:"timestamp"`
	Operator     string            `json:"operator"`
	Action       ActionType        `json:"action"`
	Status       string            `json:"status"`
	SourceRepo   string            `json:"source_repo,omitempty"`
	SourceTag    string            `json:"source_tag,omitempty"`
	TargetRepo   string            `json:"target_repo,omitempty"`
	TargetTag    string            `json:"target_tag,omitempty"`
	Digest       string            `json:"digest,omitempty"`
	Size         int64             `json:"size,omitempty"`
	Duration     time.Duration     `json:"duration,omitempty"`
	ErrorMessage string            `json:"error_message,omitempty"`
	Extra        map[string]string `json:"extra,omitempty"`
}

type AuditLogger struct {
	mu       sync.RWMutex
	logFile  *os.File
	entries  []AuditEntry
	logPath  string
	operator string
	batchSize int
}

type AuditLogConfig struct {
	LogPath  string
	Operator string
	BatchSize int
}

func NewAuditLogger(config AuditLogConfig) (*AuditLogger, error) {
	if config.BatchSize <= 0 {
		config.BatchSize = 100
	}

	dir := filepath.Dir(config.LogPath)
	if dir != "" && dir != "." {
		if err := os.MkdirAll(dir, 0750); err != nil {
			return nil, fmt.Errorf("failed to create log directory: %w", err)
		}
	}

	f, err := os.OpenFile(config.LogPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0640)
	if err != nil {
		return nil, fmt.Errorf("failed to open audit log file: %w", err)
	}

	return &AuditLogger{
		logFile:   f,
		logPath:   config.LogPath,
		operator:  config.Operator,
		batchSize: config.BatchSize,
		entries:   make([]AuditEntry, 0, config.BatchSize),
	}, nil
}

func (al *AuditLogger) LogSync(
	sourceRepo, sourceTag, targetRepo, targetTag, digest string,
	size int64,
	duration time.Duration,
	err error,
) {
	status := "SUCCESS"
	errMsg := ""
	if err != nil {
		status = "FAILED"
		errMsg = err.Error()
	}

	al.log(AuditEntry{
		ID:         generateID(),
		Timestamp:  time.Now(),
		Operator:   al.operator,
		Action:     ActionSync,
		Status:     status,
		SourceRepo: sourceRepo,
		SourceTag:  sourceTag,
		TargetRepo: targetRepo,
		TargetTag:  targetTag,
		Digest:     digest,
		Size:       size,
		Duration:   duration,
		ErrorMessage: errMsg,
	})
}

func (al *AuditLogger) LogSkip(
	sourceRepo, sourceTag, reason string,
) {
	al.log(AuditEntry{
		ID:        generateID(),
		Timestamp: time.Now(),
		Operator:  al.operator,
		Action:    ActionSkip,
		Status:    "SKIPPED",
		SourceRepo: sourceRepo,
		SourceTag:  sourceTag,
		Extra: map[string]string{
			"reason": reason,
		},
	})
}

func (al *AuditLogger) LogDelete(
	repo, tag string,
	manifestDigest string,
	err error,
) {
	status := "SUCCESS"
	errMsg := ""
	if err != nil {
		status = "FAILED"
		errMsg = err.Error()
	}

	al.log(AuditEntry{
		ID:        generateID(),
		Timestamp: time.Now(),
		Operator:  al.operator,
		Action:    ActionDelete,
		Status:    status,
		TargetRepo: repo,
		TargetTag:  tag,
		Digest:     manifestDigest,
		ErrorMessage: errMsg,
	})
}

func (al *AuditLogger) LogPush(
	repo, tag, digest string,
	size int64,
	duration time.Duration,
	err error,
) {
	status := "SUCCESS"
	errMsg := ""
	if err != nil {
		status = "FAILED"
		errMsg = err.Error()
	}

	al.log(AuditEntry{
		ID:        generateID(),
		Timestamp: time.Now(),
		Operator:  al.operator,
		Action:    ActionPush,
		Status:    status,
		TargetRepo: repo,
		TargetTag:  tag,
		Digest:     digest,
		Size:       size,
		Duration:   duration,
		ErrorMessage: errMsg,
	})
}

func (al *AuditLogger) LogVerify(
	repo, tag, digest string,
	verified bool,
	err error,
) {
	status := "SUCCESS"
	errMsg := ""
	if err != nil {
		status = "FAILED"
		errMsg = err.Error()
	} else if !verified {
		status = "MISMATCH"
	}

	al.log(AuditEntry{
		ID:        generateID(),
		Timestamp: time.Now(),
		Operator:  al.operator,
		Action:    ActionVerify,
		Status:    status,
		TargetRepo: repo,
		TargetTag:  tag,
		Digest:     digest,
		ErrorMessage: errMsg,
	})
}

func (al *AuditLogger) LogRelay(
	sourceRepo, targetRepo, digest string,
	relayNode string,
	action string,
	duration time.Duration,
	err error,
) {
	status := "SUCCESS"
	errMsg := ""
	if err != nil {
		status = "FAILED"
		errMsg = err.Error()
	}

	al.log(AuditEntry{
		ID:        generateID(),
		Timestamp: time.Now(),
		Operator:  al.operator,
		Action:    ActionRelay,
		Status:    status,
		SourceRepo: sourceRepo,
		TargetRepo: targetRepo,
		Digest:     digest,
		Duration:   duration,
		ErrorMessage: errMsg,
		Extra: map[string]string{
			"relay_node": relayNode,
			"relay_action": action,
		},
	})
}

func (al *AuditLogger) log(entry AuditEntry) {
	al.mu.Lock()
	defer al.mu.Unlock()

	al.entries = append(al.entries, entry)

	if len(al.entries) >= al.batchSize {
		al.flushLocked()
	}
}

func (al *AuditLogger) flushLocked() {
	if len(al.entries) == 0 {
		return
	}

	for _, entry := range al.entries {
		data, err := json.Marshal(entry)
		if err != nil {
			continue
		}
		fmt.Fprintf(al.logFile, "%s\n", data)
	}

	al.logFile.Sync()
	al.entries = al.entries[:0]
}

func (al *AuditLogger) Flush() {
	al.mu.Lock()
	defer al.mu.Unlock()
	al.flushLocked()
}

func (al *AuditLogger) Close() error {
	al.mu.Lock()
	defer al.mu.Unlock()

	al.flushLocked()
	return al.logFile.Close()
}

func (al *AuditLogger) ReadLogs(count int) ([]AuditEntry, error) {
	al.mu.RLock()
	defer al.mu.RUnlock()

	f, err := os.Open(al.logPath)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var entries []AuditEntry
	decoder := json.NewDecoder(f)

	for {
		var entry AuditEntry
		if err := decoder.Decode(&entry); err == io.EOF {
			break
		} else if err != nil {
			continue
		}
		entries = append(entries, entry)
	}

	if len(entries) > count && count > 0 {
		entries = entries[len(entries)-count:]
	}

	return entries, nil
}

func (al *AuditLogger) GetOperator() string {
	return al.operator
}

func (al *AuditLogger) SetOperator(operator string) {
	al.mu.Lock()
	defer al.mu.Unlock()
	al.operator = operator
}

func (al *AuditLogger) GetSummary() map[string]interface{} {
	al.mu.RLock()
	defer al.mu.RUnlock()

	summary := map[string]interface{}{
		"total_entries": len(al.entries),
		"operator":      al.operator,
		"log_path":      al.logPath,
	}

	actions := make(map[ActionType]int)
	statuses := make(map[string]int)

	entries := append([]AuditEntry{}, al.entries...)
	al.mu.RUnlock()

	f, err := os.Open(al.logPath)
	al.mu.RLock()
	if err == nil {
		decoder := json.NewDecoder(f)
		for {
			var entry AuditEntry
			if err := decoder.Decode(&entry); err == io.EOF {
				break
			} else if err != nil {
				continue
			}
			entries = append(entries, entry)
		}
		f.Close()
	}

	for _, entry := range entries {
		actions[entry.Action]++
		statuses[entry.Status]++
	}

	summary["actions"] = actions
	summary["statuses"] = statuses

	return summary
}

func generateID() string {
	return fmt.Sprintf("audit-%d-%d", time.Now().UnixNano(), time.Now().UnixMilli())
}
