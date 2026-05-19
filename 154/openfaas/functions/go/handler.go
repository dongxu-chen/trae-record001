package function

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"strings"
	"time"
)

type EventHandler struct {
	slackWebhook    string
	teamsWebhook    string
	dingtalkWebhook string
}

type K8sEvent struct {
	Type   string   `json:"type"`
	Object EventObj `json:"object"`
}

type EventObj struct {
	Metadata       Metadata       `json:"metadata"`
	InvolvedObject InvolvedObject `json:"involvedObject"`
	Reason         string         `json:"reason"`
	Message        string         `json:"message"`
	Type           string         `json:"type"`
	FirstTimestamp string         `json:"firstTimestamp"`
	LastTimestamp  string         `json:"lastTimestamp"`
	Count          int            `json:"count"`
	Source         Source         `json:"source"`
}

type Metadata struct {
	Name      string `json:"name"`
	Namespace string `json:"namespace"`
}

type InvolvedObject struct {
	Name      string `json:"name"`
	Namespace string `json:"namespace"`
	Kind      string `json:"kind"`
}

type Source struct {
	Component string `json:"component"`
}

type HandlerResponse struct {
	Status        string         `json:"status"`
	EventType     string         `json:"event_type"`
	Notifications []Notification `json:"notifications"`
	Error         string         `json:"error,omitempty"`
}

type Notification struct {
	Channel string `json:"channel"`
	Status  string `json:"status"`
}

func NewEventHandler() *EventHandler {
	return &EventHandler{
		slackWebhook:    os.Getenv("SLACK_WEBHOOK_URL"),
		teamsWebhook:    os.Getenv("TEAMS_WEBHOOK_URL"),
		dingtalkWebhook: os.Getenv("DINGTALK_WEBHOOK_URL"),
	}
}

func (h *EventHandler) Handle(event K8sEvent) HandlerResponse {
	fmt.Printf("Processing event: %s\n", event.Object.Reason)

	result := HandlerResponse{
		Status:        "processed",
		EventType:     event.Type,
		Notifications: []Notification{},
	}

	eventData := h.extractEventData(event.Object)

	if h.slackWebhook != "" {
		status := h.sendSlackNotification(eventData)
		result.Notifications = append(result.Notifications, Notification{
			Channel: "slack",
			Status:  status,
		})
	}

	if h.teamsWebhook != "" {
		status := h.sendTeamsNotification(eventData)
		result.Notifications = append(result.Notifications, Notification{
			Channel: "teams",
			Status:  status,
		})
	}

	if h.dingtalkWebhook != "" {
		status := h.sendDingtalkNotification(eventData)
		result.Notifications = append(result.Notifications, Notification{
			Channel: "dingtalk",
			Status:  status,
		})
	}

	return result
}

func (h *EventHandler) extractEventData(obj EventObj) map[string]interface{} {
	name := obj.InvolvedObject.Name
	if name == "" {
		name = obj.Metadata.Name
	}
	if name == "" {
		name = "Unknown"
	}

	namespace := obj.InvolvedObject.Namespace
	if namespace == "" {
		namespace = obj.Metadata.Namespace
	}
	if namespace == "" {
		namespace = "default"
	}

	kind := obj.InvolvedObject.Kind
	if kind == "" {
		kind = "Unknown"
	}

	reason := obj.Reason
	if reason == "" {
		reason = "Unknown"
	}

	message := obj.Message
	if message == "" {
		message = "No message"
	}

	eventType := obj.Type
	if eventType == "" {
		eventType = "Normal"
	}

	count := obj.Count
	if count == 0 {
		count = 1
	}

	return map[string]interface{}{
		"name":            name,
		"namespace":       namespace,
		"kind":            kind,
		"reason":          reason,
		"message":         message,
		"type":            eventType,
		"first_timestamp": obj.FirstTimestamp,
		"last_timestamp":  obj.LastTimestamp,
		"count":           count,
		"source":          obj.Source.Component,
	}
}

func (h *EventHandler) sendSlackNotification(eventData map[string]interface{}) string {
	color := "#36a64f"
	if eventData["type"] != "Normal" {
		color = "#ff0000"
	}

	message := eventData["message"].(string)
	if len(message) > 500 {
		message = message[:500]
	}

	payload := map[string]interface{}{
		"text": fmt.Sprintf("K8s Event: %s - %s", eventData["reason"], eventData["name"]),
		"blocks": []map[string]interface{}{
			{
				"type": "header",
				"text": map[string]string{
					"type": "plain_text",
					"text": fmt.Sprintf("Kubernetes Event: %s", eventData["reason"]),
				},
			},
			{
				"type": "section",
				"fields": []map[string]string{
					{"type": "mrkdwn", "text": fmt.Sprintf("*Type:*\n%s", eventData["type"])},
					{"type": "mrkdwn", "text": fmt.Sprintf("*Namespace:*\n%s", eventData["namespace"])},
					{"type": "mrkdwn", "text": fmt.Sprintf("*Name:*\n%s", eventData["name"])},
					{"type": "mrkdwn", "text": fmt.Sprintf("*Count:*\n%d", eventData["count"])},
				},
			},
			{
				"type": "section",
				"text": map[string]string{
					"type": "mrkdwn",
					"text": fmt.Sprintf("*Message:*\n```%s```", message),
				},
			},
		},
	}

	return h.sendWebhook(h.slackWebhook, payload)
}

func (h *EventHandler) sendTeamsNotification(eventData map[string]interface{}) string {
	themeColor := "00FF00"
	if eventData["type"] != "Normal" {
		themeColor = "FF0000"
	}

	message := eventData["message"].(string)
	if len(message) > 500 {
		message = message[:500]
	}

	card := map[string]interface{}{
		"type": "message",
		"attachments": []map[string]interface{}{
			{
				"contentType": "application/vnd.microsoft.card.adaptive",
				"content": map[string]interface{}{
					"type":        "AdaptiveCard",
					"version":     "1.2",
					"themeColor":  themeColor,
					"body": []map[string]interface{}{
						{
							"type":   "TextBlock",
							"size":   "Large",
							"weight": "Bolder",
							"text":   fmt.Sprintf("Kubernetes Event: %s", eventData["reason"]),
						},
						{
							"type": "FactSet",
							"facts": []map[string]string{
								{"title": "Type", "value": eventData["type"].(string)},
								{"title": "Namespace", "value": eventData["namespace"].(string)},
								{"title": "Name", "value": eventData["name"].(string)},
								{"title": "Count", "value": fmt.Sprintf("%d", eventData["count"])},
							},
						},
						{
							"type": "TextBlock",
							"text": message,
							"wrap": true,
						},
					},
				},
			},
		},
	}

	return h.sendWebhook(h.teamsWebhook, card)
}

func (h *EventHandler) sendDingtalkNotification(eventData map[string]interface{}) string {
	message := eventData["message"].(string)
	if len(message) > 500 {
		message = message[:500]
	}

	markdownText := fmt.Sprintf(`### Kubernetes Event: %s

**Type**: %s
**Namespace**: %s
**Name**: %s
**Count**: %d

**Message**:
%s`,
		eventData["reason"],
		eventData["type"],
		eventData["namespace"],
		eventData["name"],
		eventData["count"],
		message,
	)

	payload := map[string]interface{}{
		"msgtype": "markdown",
		"markdown": map[string]string{
			"title": fmt.Sprintf("K8s Event: %s", eventData["reason"]),
			"text":  markdownText,
		},
	}

	return h.sendWebhook(h.dingtalkWebhook, payload)
}

func (h *EventHandler) sendWebhook(url string, payload interface{}) string {
	jsonData, err := json.Marshal(payload)
	if err != nil {
		return fmt.Sprintf("failed: %v", err)
	}

	client := &http.Client{Timeout: 10 * time.Second}
	resp, err := client.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Sprintf("failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 200 && resp.StatusCode < 300 {
		return "sent"
	}
	return fmt.Sprintf("failed: status %d", resp.StatusCode)
}

func Handle(req []byte) string {
	var event K8sEvent
	if err := json.Unmarshal(req, &event); err != nil {
		response, _ := json.Marshal(HandlerResponse{
			Status: "error",
			Error:  err.Error(),
		})
		return string(response)
	}

	handler := NewEventHandler()
	result := handler.Handle(event)

	response, _ := json.Marshal(result)
	return string(response)
}
