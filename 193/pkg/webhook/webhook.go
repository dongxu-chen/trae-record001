package webhook

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"

	"k8s-auditor/pkg/audit"
	"k8s-auditor/pkg/config"
)

type WebhookNotifier struct {
	cfg    config.WebhookConfig
	client *http.Client
}

type WebhookPayload struct {
	Timestamp            time.Time                `json:"timestamp"`
	Cluster              string                   `json:"cluster"`
	TotalResources       int                      `json:"total_resources"`
	ViolationCount       int                      `json:"violation_count"`
	Summary              map[string]int           `json:"summary"`
	Violations           []ViolationInfo          `json:"violations"`
	NamespaceQuotaUsages []NamespaceQuotaUsageInfo `json:"namespace_quota_usages"`
}

type ViolationInfo struct {
	ResourceType string `json:"resource_type"`
	Namespace    string `json:"namespace"`
	ResourceName string `json:"resource_name"`
	RuleType     string `json:"rule_type"`
	Severity     string `json:"severity"`
	Message      string `json:"message"`
	Suggestion   string `json:"suggestion"`
}

type NamespaceQuotaUsageInfo struct {
	Namespace     string  `json:"namespace"`
	CPURequests   string  `json:"cpu_requests"`
	CPULimits     string  `json:"cpu_limits"`
	MemRequests   string  `json:"mem_requests"`
	MemLimits     string  `json:"mem_limits"`
	CPUQuota      string  `json:"cpu_quota"`
	MemQuota      string  `json:"mem_quota"`
	CPUPercent    float64 `json:"cpu_percent"`
	MemoryPercent float64 `json:"memory_percent"`
	OverQuota     bool    `json:"over_quota"`
}

func New(cfg config.WebhookConfig) *WebhookNotifier {
	timeout, _ := time.ParseDuration(cfg.Timeout)
	if timeout == 0 {
		timeout = 30 * time.Second
	}

	return &WebhookNotifier{
		cfg: cfg,
		client: &http.Client{
			Timeout: timeout,
		},
	}
}

func (w *WebhookNotifier) Enabled() bool {
	return w.cfg.Enabled && w.cfg.URL != ""
}

func (w *WebhookNotifier) Send(report *audit.AuditReport) error {
	if !w.Enabled() {
		return nil
	}

	payload := w.buildPayload(report)
	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal payload: %w", err)
	}

	req, err := http.NewRequest("POST", w.cfg.URL, bytes.NewBuffer(body))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Audit-Timestamp", fmt.Sprintf("%d", report.Timestamp.Unix()))

	if w.cfg.Secret != "" {
		signature := w.sign(body)
		req.Header.Set("X-Audit-Signature", "sha256="+signature)
	}

	resp, err := w.client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send webhook: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		respBody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("webhook returned non-success status %d: %s", resp.StatusCode, string(respBody))
	}

	return nil
}

func (w *WebhookNotifier) buildPayload(report *audit.AuditReport) WebhookPayload {
	violations := make([]ViolationInfo, 0, len(report.Violations))
	for _, v := range report.Violations {
		violations = append(violations, ViolationInfo{
			ResourceType: v.ResourceType,
			Namespace:    v.Namespace,
			ResourceName: v.ResourceName,
			RuleType:     v.RuleType,
			Severity:     string(v.Severity),
			Message:      v.Message,
			Suggestion:   v.Suggestion,
		})
	}

	quotaUsages := make([]NamespaceQuotaUsageInfo, 0, len(report.NamespaceQuotaUsages))
	for _, u := range report.NamespaceQuotaUsages {
		quotaUsages = append(quotaUsages, NamespaceQuotaUsageInfo{
			Namespace:     u.Namespace,
			CPURequests:   u.CPURequests,
			CPULimits:     u.CPULimits,
			MemRequests:   u.MemRequests,
			MemLimits:     u.MemLimits,
			CPUQuota:      u.CPUQuota,
			MemQuota:      u.MemQuota,
			CPUPercent:    u.CPUPercent,
			MemoryPercent: u.MemoryPercent,
			OverQuota:     u.OverQuota,
		})
	}

	return WebhookPayload{
		Timestamp:            report.Timestamp,
		Cluster:              report.Cluster,
		TotalResources:       report.TotalResources,
		ViolationCount:       len(report.Violations),
		Summary:              report.Summary,
		Violations:           violations,
		NamespaceQuotaUsages: quotaUsages,
	}
}

func (w *WebhookNotifier) sign(body []byte) string {
	mac := hmac.New(sha256.New, []byte(w.cfg.Secret))
	mac.Write(body)
	return hex.EncodeToString(mac.Sum(nil))
}
