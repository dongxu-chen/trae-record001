package alert

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/traffic-mirror/control-plane/pkg/types"
	"gorm.io/gorm"
)

type Manager struct {
	store *Store
	db    *gorm.DB
}

func NewManager(db *gorm.DB, store *Store) *Manager {
	return &Manager{
		store: store,
		db:    db,
	}
}

func (m *Manager) ProcessComparison(result *types.ComparisonResult) error {
	if result.Anomaly == "" {
		return nil
	}

	alert := &types.AnomalyAlert{
		Timestamp:   result.Timestamp,
		RequestID:   result.RequestID,
		Path:        result.Path,
		Method:      result.Method,
		AnomalyType: result.Anomaly,
		Severity:    "warning",
		Message:     fmt.Sprintf("Anomaly detected: %s", result.Anomaly),
		Details:     make(map[string]string),
	}

	alert.Details["prod_status"] = fmt.Sprintf("%d", result.ProdStatus)
	alert.Details["test_status"] = fmt.Sprintf("%d", result.TestStatus)
	alert.Details["body_match"] = fmt.Sprintf("%v", result.BodyMatch)
	alert.Details["severity"] = result.Severity
	alert.Details["has_diff"] = fmt.Sprintf("%v", result.HasDiff)

	if result.ProdBodyLen > 0 {
		alert.Details["prod_body_len"] = fmt.Sprintf("%d", result.ProdBodyLen)
	}
	if result.TestBodyLen > 0 {
		alert.Details["test_body_len"] = fmt.Sprintf("%d", result.TestBodyLen)
	}

	switch result.Anomaly {
	case "error_5xx":
		alert.Severity = "critical"
	case "timeout":
		alert.Severity = "critical"
	case "critical_diff":
		alert.Severity = "critical"
	case "error_4xx":
		alert.Severity = "warning"
	case "body_mismatch_severe":
		alert.Severity = "warning"
	}

	if len(result.Differences) > 0 {
		diffJSON, _ := json.Marshal(result.Differences)
		alert.Details["differences"] = string(diffJSON)
	}

	if result.Anomaly != "" {
		alert.Details["proto_differences"] = "true"
	}

	alert.Timestamp = time.Now().UnixNano()

	return m.store.Create(alert)
}

func (m *Manager) GetStore() *Store {
	return m.store
}
