package alert

import (
	"bytes"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/sirupsen/logrus"
	"github.com/google/uuid"

	"github.com/security/container-escape-detector/pkg/types"
)

type Config struct {
	LogLevel     types.RiskLevel    `yaml:"log_level"`
	WebhookURL   string            `yaml:"webhook_url"`
	WebhookToken string           `yaml:"webhook_token"`
	SMTPConfig   *SMTPConfig      `yaml:"smtp,omitempty"`
	SlackConfig  *SlackConfig     `yaml:"slack,omitempty"`
	RateLimit    int               `yaml:"rate_limit"`
	Aggregation  *AggregationConfig `yaml:"aggregation,omitempty"`
}

type SMTPConfig struct {
	Host     string `yaml:"host"`
	Port     int    `yaml:"port"`
	Username string `yaml:"username"`
	Password string `yaml:"password"`
	From     string `yaml:"from"`
	To       []string `yaml:"to"`
}

type SlackConfig struct {
	WebhookURL string `yaml:"webhook_url"`
	Channel    string `yaml:"channel"`
}

type Manager struct {
	config       *Config
	logger       *logrus.Logger
	alertChan    chan *types.Alert
	stopChan     chan struct{}
	wg           sync.WaitGroup
	alertHistory map[string]time.Time
	recentAlerts []types.Alert
	historyMu    sync.Mutex
	handlers     []AlertHandler
	mu           sync.RWMutex
	aggregator   *AlertAggregator
}

type AlertHandler interface {
	Send(alert *types.Alert) error
	Name() string
}

type LogHandler struct {
	logger   *logrus.Logger
	minLevel types.RiskLevel
}

type WebhookHandler struct {
	url    string
	token  string
	client *http.Client
	logger *logrus.Logger
}

type SlackMessage struct {
	Text        string       `json:"text"`
	Attachments []Attachment `json:"attachments,omitempty"`
}

type Attachment struct {
	Color  string `json:"color"`
	Title  string `json:"title"`
	Text   string `json:"text"`
	Fields []Field `json:"fields,omitempty"`
}

type Field struct {
	Title string `json:"title"`
	Value string `json:"value"`
	Short bool   `json:"short"`
}

func NewManager(logger *logrus.Logger, config *Config) *Manager {
	if config == nil {
		config = &Config{
			LogLevel:  types.RiskInfo,
			RateLimit: 60,
		}
	}

	m := &Manager{
		config:       config,
		logger:       logger,
		alertChan:    make(chan *types.Alert, 1000),
		stopChan:     make(chan struct{}),
		alertHistory: make(map[string]time.Time),
	}

	m.handlers = append(m.handlers, &LogHandler{
		logger:   logger,
		minLevel: config.LogLevel,
	})

	if config.WebhookURL != "" {
		m.handlers = append(m.handlers, &WebhookHandler{
			url:    config.WebhookURL,
			token:  config.WebhookToken,
			logger: logger,
			client: &http.Client{
				Timeout: 10 * time.Second,
				Transport: &http.Transport{
					TLSClientConfig: &tls.Config{InsecureSkipVerify: false},
				},
			},
		})
	}

	if config.Aggregation != nil && config.Aggregation.Enabled {
		m.aggregator = NewAlertAggregator(config.Aggregation)
		m.aggregator.SetLogger(logger)
		m.aggregator.SetSendCallback(m.sendAggregatedAlert)
	}

	return m
}

func (m *Manager) Start() error {
	if m.aggregator != nil {
		m.aggregator.Start()
	}

	m.wg.Add(1)
	go m.processAlerts()

	m.logger.Infof("Alert manager started with %d handlers", len(m.handlers))
	return nil
}

func (m *Manager) processAlerts() {
	defer m.wg.Done()

	for {
		select {
		case <-m.stopChan:
			return
		case alert := <-m.alertChan:
			if m.isRateLimited(alert) {
				m.logger.Debugf("Alert %s rate limited, skipping", alert.ID)
				continue
			}

			if m.aggregator != nil {
				if m.aggregator.AddAlert(alert) {
					m.logger.Debugf("Alert %s added to aggregator", alert.ID)
					continue
				}
			}

			m.sendAlert(alert)
		}
	}
}

func (m *Manager) sendAggregatedAlert(aggregated *AggregatedAlert) {
	if aggregated == nil {
		return
	}

	m.logger.Infof("Sending aggregated alert: %d alerts of type %s",
		aggregated.AlertCount, aggregated.RuleID)

	if len(m.handlers) == 0 {
		return
	}

	for _, handler := range m.handlers {
		handlerName := handler.Name()

		switch handlerName {
		case "log":
			m.sendAggregatedToLog(aggregated)
		case "webhook":
			m.sendAggregatedToWebhook(aggregated)
		default:
			if aggregated.Representative != nil {
				if err := handler.Send(aggregated.Representative); err != nil {
					m.logger.Errorf("Failed to send alert via %s: %v", handlerName, err)
				}
			}
		}
	}
}

func (m *Manager) sendAggregatedToLog(aggregated *AggregatedAlert) {
	logHandler, ok := m.handlers[0].(*LogHandler)
	if !ok {
		return
	}

	if !isSeverityAtLeast(aggregated.Severity, logHandler.minLevel) {
		return
	}

	logFields := logrus.Fields{
		"aggregated_id":   aggregated.ID,
		"severity":        aggregated.Severity,
		"rule_id":         aggregated.RuleID,
		"container_id":    aggregated.ContainerID,
		"container_name":  aggregated.ContainerName,
		"alert_count":     aggregated.AlertCount,
		"unique_pids":     len(aggregated.UniquePIDs),
		"window_start":    aggregated.FirstSeen,
		"window_end":      aggregated.LastSeen,
	}

	message := fmt.Sprintf("[%s] AGGREGATED %d alerts: %s",
		aggregated.Severity, aggregated.AlertCount, aggregated.AggregatedDescription)

	for i, ev := range aggregated.AggregatedEvidence {
		logFields[fmt.Sprintf("evidence_%d", i)] = ev
	}

	switch aggregated.Severity {
	case types.RiskCritical:
		logHandler.logger.WithFields(logFields).Error(message)
	case types.RiskHigh:
		logHandler.logger.WithFields(logFields).Error(message)
	case types.RiskMedium:
		logHandler.logger.WithFields(logFields).Warn(message)
	case types.RiskLow:
		logHandler.logger.WithFields(logFields).Info(message)
	default:
		logHandler.logger.WithFields(logFields).Debug(message)
	}
}

func (m *Manager) sendAggregatedToWebhook(aggregated *AggregatedAlert) {
	for _, handler := range m.handlers {
		if wh, ok := handler.(*WebhookHandler); ok {
			payload := map[string]interface{}{
				"aggregated_id":        aggregated.ID,
				"timestamp":            aggregated.Timestamp,
				"severity":             aggregated.Severity,
				"rule_id":              aggregated.RuleID,
				"rule_name":            aggregated.RuleName,
				"container_id":         aggregated.ContainerID,
				"container_name":       aggregated.ContainerName,
				"alert_count":          aggregated.AlertCount,
				"first_seen":           aggregated.FirstSeen,
				"last_seen":            aggregated.LastSeen,
				"unique_pids":          aggregated.UniquePIDs,
				"unique_comms":         aggregated.UniqueComms,
				"aggregated_evidence":  aggregated.AggregatedEvidence,
				"description":          aggregated.AggregatedDescription,
				"representative":       aggregated.Representative,
			}

			body, err := json.Marshal(payload)
			if err != nil {
				m.logger.Errorf("Failed to marshal aggregated alert: %v", err)
				return
			}

			req, err := http.NewRequest("POST", wh.url, bytes.NewBuffer(body))
			if err != nil {
				m.logger.Errorf("Failed to create webhook request: %v", err)
				return
			}

			req.Header.Set("Content-Type", "application/json")
			if wh.token != "" {
				req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", wh.token))
			}

			resp, err := wh.client.Do(req)
			if err != nil {
				m.logger.Errorf("Failed to send aggregated webhook: %v", err)
				return
			}
			defer resp.Body.Close()

			if resp.StatusCode >= 400 {
				m.logger.Errorf("Aggregated webhook returned status code %d", resp.StatusCode)
			} else {
				m.logger.Debugf("Aggregated alert sent via webhook: %s", aggregated.ID)
			}
		}
	}
}

func (m *Manager) isRateLimited(alert *types.Alert) bool {
	if m.config.RateLimit <= 0 {
		return false
	}

	key := fmt.Sprintf("%s-%d-%s", alert.RuleID, alert.ProcessPID, alert.ContainerID)

	m.historyMu.Lock()
	defer m.historyMu.Unlock()

	if lastSent, exists := m.alertHistory[key]; exists {
		if time.Since(lastSent) < time.Duration(m.config.RateLimit)*time.Second {
			return true
		}
	}

	m.alertHistory[key] = time.Now()
	return false
}

func (m *Manager) sendAlert(alert *types.Alert) {
	m.mu.Lock()
	m.recentAlerts = append(m.recentAlerts, *alert)
	if len(m.recentAlerts) > 1000 {
		m.recentAlerts = m.recentAlerts[1:]
	}
	m.mu.Unlock()

	for _, handler := range m.handlers {
		if err := handler.Send(alert); err != nil {
			m.logger.Errorf("Failed to send alert via %s: %v", handler.Name(), err)
		}
	}
}

func (m *Manager) GetRecentAlerts(max int) []types.Alert {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if max <= 0 || max > len(m.recentAlerts) {
		max = len(m.recentAlerts)
	}

	result := make([]types.Alert, max)
	copy(result, m.recentAlerts[len(m.recentAlerts)-max:])
	return result
}

func (m *Manager) GenerateAlert(
	event *types.BPFEvent,
	container *types.ContainerInfo,
	rule *types.DetectionRule,
	profile *types.BehaviorProfile,
	attackPath *types.AttackChain,
	node *types.ProcessNode,
) *types.Alert {
	alert := &types.Alert{
		ID:            generateAlertID(),
		Timestamp:     time.Now(),
		Severity:      rule.Severity,
		Title:         rule.Name,
		Description:   rule.Description,
		RuleID:        rule.ID,
		RiskScore:     rule.Score,
		Mitigation:    rule.Mitigation,
		AttackPath:    attackPath,
	}

	if container != nil {
		alert.ContainerID = container.ID
		alert.ContainerName = container.Name
	}

	if event != nil {
		alert.ProcessPID = int(event.PID)
		alert.ProcessComm = event.Comm
		alert.Evidence = m.generateEvidence(event, rule, node)
	}

	if profile != nil && profile.RiskScore > alert.RiskScore {
		alert.RiskScore = profile.RiskScore
	}

	return alert
}

func (m *Manager) generateEvidence(event *types.BPFEvent, rule *types.DetectionRule, node *types.ProcessNode) []string {
	var evidence []string

	evidence = append(evidence, fmt.Sprintf("Rule matched: %s (%s)", rule.ID, rule.Name))

	if event != nil {
		evidence = append(evidence, fmt.Sprintf("Event: %s at %s", event.EventType, event.Timestamp.Format(time.RFC3339)))
		evidence = append(evidence, fmt.Sprintf("Process: PID=%d, PPID=%d, COMM=%s, UID=%d, GID=%d",
			event.PID, event.PPID, event.Comm, event.UID, event.GID))

		if event.SyscallName != "" {
			evidence = append(evidence, fmt.Sprintf("Syscall: %s (nr=%d)", event.SyscallName, event.SyscallNr))
		}

		if event.MountSource != "" || event.MountTarget != "" {
			evidence = append(evidence, fmt.Sprintf("Mount: %s -> %s (type=%s, flags=0x%x)",
				event.MountSource, event.MountTarget, event.FSType, event.MountFlags))
		}

		if event.CapName != "" {
			evidence = append(evidence, fmt.Sprintf("Capability: %s (action=%s)", event.CapName, event.CapAction))
		}

		if event.FileName != "" {
			evidence = append(evidence, fmt.Sprintf("File: %s (flags=0x%x)", event.FileName, event.FileFlags))
		}

		evidence = append(evidence, fmt.Sprintf("Namespaces: PIDNS=%d, MNTNS=%d", event.PIDNS, event.MNTNS))
	}

	if node != nil && len(node.RiskTags) > 0 {
		evidence = append(evidence, fmt.Sprintf("Risk tags: %v", node.RiskTags))
	}

	return evidence
}

func (m *Manager) Send(alert *types.Alert) {
	select {
	case m.alertChan <- alert:
	default:
		m.logger.Warn("Alert channel full, dropping alert")
	}
}

func (m *Manager) Close() {
	close(m.stopChan)
	m.wg.Wait()

	if m.aggregator != nil {
		m.aggregator.Stop()
	}

	close(m.alertChan)
	m.logger.Info("Alert manager closed")
}

func (m *Manager) GetAggregationStats() map[string]interface{} {
	if m.aggregator == nil {
		return map[string]interface{}{"enabled": false}
	}
	return m.aggregator.GetGroupStats()
}

func (h *LogHandler) Send(alert *types.Alert) error {
	if !isSeverityAtLeast(alert.Severity, h.minLevel) {
		return nil
	}

	logFields := logrus.Fields{
		"alert_id":       alert.ID,
		"severity":       alert.Severity,
		"rule_id":        alert.RuleID,
		"container_id":   alert.ContainerID,
		"container_name": alert.ContainerName,
		"process_pid":    alert.ProcessPID,
		"process_comm":   alert.ProcessComm,
		"risk_score":     alert.RiskScore,
	}

	message := fmt.Sprintf("[%s] %s: %s", alert.Severity, alert.Title, alert.Description)

	if alert.AttackPath != nil {
		logFields["attack_path"] = alert.AttackPath.Description
		logFields["attack_steps"] = len(alert.AttackPath.Steps)
		logFields["total_score"] = alert.AttackPath.TotalScore
	}

	for i, ev := range alert.Evidence {
		logFields[fmt.Sprintf("evidence_%d", i)] = ev
	}

	switch alert.Severity {
	case types.RiskCritical:
		h.logger.WithFields(logFields).Error(message)
	case types.RiskHigh:
		h.logger.WithFields(logFields).Error(message)
	case types.RiskMedium:
		h.logger.WithFields(logFields).Warn(message)
	case types.RiskLow:
		h.logger.WithFields(logFields).Info(message)
	default:
		h.logger.WithFields(logFields).Debug(message)
	}

	return nil
}

func (h *LogHandler) Name() string {
	return "log"
}

func (h *WebhookHandler) Send(alert *types.Alert) error {
	payload := map[string]interface{}{
		"alert_id":       alert.ID,
		"timestamp":      alert.Timestamp,
		"severity":       alert.Severity,
		"title":          alert.Title,
		"description":    alert.Description,
		"container_id":   alert.ContainerID,
		"container_name": alert.ContainerName,
		"process_pid":    alert.ProcessPID,
		"process_comm":   alert.ProcessComm,
		"rule_id":        alert.RuleID,
		"risk_score":     alert.RiskScore,
		"evidence":       alert.Evidence,
		"mitigation":     alert.Mitigation,
	}

	if alert.AttackPath != nil {
		payload["attack_path"] = alert.AttackPath
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal alert: %w", err)
	}

	req, err := http.NewRequest("POST", h.url, bytes.NewBuffer(body))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	if h.token != "" {
		req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", h.token))
	}

	resp, err := h.client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send webhook: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 400 {
		return fmt.Errorf("webhook returned status code %d", resp.StatusCode)
	}

	h.logger.Debugf("Alert sent via webhook: %s", alert.ID)
	return nil
}

func (h *WebhookHandler) Name() string {
	return "webhook"
}

func (h *LogHandler) SendSlack(alert *types.Alert) error {
	if h.logger == nil {
		return nil
	}
	return nil
}

func isSeverityAtLeast(current, min types.RiskLevel) bool {
	severityOrder := map[types.RiskLevel]int{
		types.RiskInfo:     0,
		types.RiskLow:      1,
		types.RiskMedium:   2,
		types.RiskHigh:     3,
		types.RiskCritical: 4,
	}

	return severityOrder[current] >= severityOrder[min]
}

func generateAlertID() string {
	return "alert-" + uuid.New().String()[:16]
}

func FormatAlertForConsole(alert *types.Alert) string {
	var buf bytes.Buffer

	fmt.Fprintf(&buf, "\n=== ALERT [%s] %s ===\n", alert.Severity, alert.Timestamp.Format(time.RFC3339))
	fmt.Fprintf(&buf, "ID: %s\n", alert.ID)
	fmt.Fprintf(&buf, "Title: %s\n", alert.Title)
	fmt.Fprintf(&buf, "Description: %s\n", alert.Description)
	fmt.Fprintf(&buf, "Rule: %s\n", alert.RuleID)
	fmt.Fprintf(&buf, "Container: %s (%s)\n", alert.ContainerName, alert.ContainerID[:12])
	fmt.Fprintf(&buf, "Process: %s (PID: %d)\n", alert.ProcessComm, alert.ProcessPID)
	fmt.Fprintf(&buf, "Risk Score: %.1f/100\n", alert.RiskScore)

	if len(alert.Evidence) > 0 {
		fmt.Fprintf(&buf, "\nEvidence:\n")
		for _, ev := range alert.Evidence {
			fmt.Fprintf(&buf, "  - %s\n", ev)
		}
	}

	if alert.AttackPath != nil {
		fmt.Fprintf(&buf, "\nAttack Path:\n")
		fmt.Fprintf(&buf, "  Description: %s\n", alert.AttackPath.Description)
		fmt.Fprintf(&buf, "  Total Score: %.1f\n", alert.AttackPath.TotalScore)
		fmt.Fprintf(&buf, "  Steps:\n")
		for _, step := range alert.AttackPath.Steps {
			fmt.Fprintf(&buf, "    %d. [%s] %s - %s (PID: %d, Score: %.1f)\n",
				step.Sequence, step.Phase, step.Action, step.Comm, step.PID, step.RiskScore)
		}
	}

	if alert.Mitigation != "" {
		fmt.Fprintf(&buf, "\nMitigation: %s\n", alert.Mitigation)
	}

	fmt.Fprintf(&buf, "==============================\n")

	return buf.String()
}
