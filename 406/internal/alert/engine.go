package alert

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"net/http"
	"net/smtp"
	"strings"
	"sync"
	"time"
	"health-check/internal/config"
	"health-check/internal/model"
	"health-check/internal/window"
)

type Engine struct {
	mu            sync.RWMutex
	cfg           *config.AlertConfig
	rules         map[string]*model.AlertRule
	activeAlerts  map[string]*model.AlertEvent
	endpointWindows map[string]*window.SlidingWindow
}

func New(cfg *config.AlertConfig, rules []model.AlertRule) *Engine {
	ruleMap := make(map[string]*model.AlertRule)
	for i := range rules {
		ruleMap[rules[i].ID] = &rules[i]
	}

	return &Engine{
		cfg:             cfg,
		rules:           ruleMap,
		activeAlerts:    make(map[string]*model.AlertEvent),
		endpointWindows: make(map[string]*window.SlidingWindow),
	}
}

func (e *Engine) RegisterEndpoint(endpointID string, win *window.SlidingWindow) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.endpointWindows[endpointID] = win
}

func (e *Engine) Evaluate(endpoint *model.Endpoint, result *model.ProbeResult) {
	if !e.cfg.Enabled {
		return
	}

	e.mu.RLock()
	win, hasWindow := e.endpointWindows[endpoint.ID]
	e.mu.RUnlock()

	if !hasWindow {
		return
	}

	stats := win.GetStats()

	for _, ruleID := range endpoint.AlertRules {
		rule, ok := e.rules[ruleID]
		if !ok {
			continue
		}

		triggered := e.checkCondition(rule, result, stats)

		alertKey := endpoint.ID + ":" + ruleID

		e.mu.Lock()
		existingAlert, exists := e.activeAlerts[alertKey]

		if triggered && !exists {
			alert := &model.AlertEvent{
				ID:          fmt.Sprintf("alert-%d", time.Now().UnixNano()),
				RuleID:      ruleID,
				EndpointID:  endpoint.ID,
				Name:        endpoint.Name,
				Severity:    rule.Severity,
				Message:     fmt.Sprintf("Endpoint %s triggered %s: availability=%.2f%%", endpoint.Name, rule.Name, stats.Availability),
				TriggeredAt: time.Now(),
				Status:      "FIRING",
			}
			e.activeAlerts[alertKey] = alert
			go e.sendNotification(rule, alert)
		} else if !triggered && exists {
			now := time.Now()
			existingAlert.ResolvedAt = &now
			existingAlert.Status = "RESOLVED"
			existingAlert.Message = fmt.Sprintf("Endpoint %s recovered: availability=%.2f%%", endpoint.Name, stats.Availability)
			go e.sendNotification(rule, existingAlert)
			delete(e.activeAlerts, alertKey)
		}
		e.mu.Unlock()
	}
}

func (e *Engine) checkCondition(rule *model.AlertRule, result *model.ProbeResult, stats *model.WindowStats) bool {
	switch rule.Condition {
	case "availability_lt":
		return stats.Availability < rule.Threshold
	case "error_rate_gt":
		return stats.ErrorRate > rule.Threshold
	case "latency_gt_ms":
		return float64(stats.P95Latency.Milliseconds()) > rule.Threshold
	case "status_down":
		return result.Status == model.StatusDown
	case "consecutive_failures":
		return stats.FailureCount >= int(rule.Threshold)
	default:
		return false
	}
}

func (e *Engine) sendNotification(rule *model.AlertRule, alert *model.AlertEvent) {
	switch rule.NotificationType {
	case "email":
		e.sendEmail(alert)
	case "webhook":
		e.sendWebhook(alert)
	case "dingtalk":
		e.sendDingTalk(alert)
	}
}

func (e *Engine) sendEmail(alert *model.AlertEvent) {
	if e.cfg.SMTP == nil {
		return
	}

	smtpCfg := e.cfg.SMTP
	auth := smtp.PlainAuth("", smtpCfg.Username, smtpCfg.Password, smtpCfg.Host)

	subject := fmt.Sprintf("[%s] %s - %s", alert.Severity, alert.Status, alert.Name)
	body := fmt.Sprintf(`
Alert Details:
==============
Endpoint: %s
Status: %s
Severity: %s
Message: %s
Triggered At: %s
`, alert.Name, alert.Status, alert.Severity, alert.Message, alert.TriggeredAt.Format(time.RFC3339))

	if alert.ResolvedAt != nil {
		body += fmt.Sprintf("Resolved At: %s\n", alert.ResolvedAt.Format(time.RFC3339))
	}

	msg := fmt.Sprintf("From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n%s",
		smtpCfg.From, strings.Join(smtpCfg.To, ","), subject, body)

	addr := fmt.Sprintf("%s:%d", smtpCfg.Host, smtpCfg.Port)
	smtp.SendMail(addr, auth, smtpCfg.From, smtpCfg.To, []byte(msg))
}

func (e *Engine) sendWebhook(alert *model.AlertEvent) {
	if e.cfg.WebhookURL == "" {
		return
	}

	data, _ := json.Marshal(alert)
	http.Post(e.cfg.WebhookURL, "application/json", bytes.NewBuffer(data))
}

func (e *Engine) sendDingTalk(alert *model.AlertEvent) {
	if e.cfg.DingTalk == nil {
		return
	}

	cfg := e.cfg.DingTalk
	timestamp := fmt.Sprintf("%d", time.Now().UnixMilli())

	stringToSign := timestamp + "\n" + cfg.Secret
	h := hmac.New(sha256.New, []byte(cfg.Secret))
	h.Write([]byte(stringToSign))
	sign := base64.StdEncoding.EncodeToString(h.Sum(nil))

	url := fmt.Sprintf("%s&timestamp=%s&sign=%s", cfg.WebhookURL, timestamp, sign)

	msg := map[string]interface{}{
		"msgtype": "markdown",
		"markdown": map[string]string{
			"title": fmt.Sprintf("[%s] %s", alert.Status, alert.Name),
			"text": fmt.Sprintf("### **%s** - %s\n\n**Endpoint**: %s\n\n**Status**: %s\n\n**Severity**: %s\n\n**Message**: %s\n\n**Time**: %s",
				alert.Status, alert.Severity, alert.Name, alert.Status, alert.Severity, alert.Message, alert.TriggeredAt.Format(time.RFC3339)),
		},
	}

	data, _ := json.Marshal(msg)
	http.Post(url, "application/json", bytes.NewBuffer(data))
}

func (e *Engine) GetActiveAlerts() []*model.AlertEvent {
	e.mu.RLock()
	defer e.mu.RUnlock()

	alerts := make([]*model.AlertEvent, 0, len(e.activeAlerts))
	for _, alert := range e.activeAlerts {
		alerts = append(alerts, alert)
	}
	return alerts
}
