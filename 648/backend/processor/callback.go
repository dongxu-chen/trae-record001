package processor

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"redis-keyspace-notifier/config"
	"redis-keyspace-notifier/logger"
	"redis-keyspace-notifier/models"
	"time"

	"go.uber.org/zap"
)

type CallbackHandler struct {
	httpClient *http.Client
}

func NewCallbackHandler() *CallbackHandler {
	return &CallbackHandler{
		httpClient: &http.Client{
			Timeout: config.AppConfig.Callback.Timeout,
		},
	}
}

func (h *CallbackHandler) HandleEvent(event *models.KeyEvent) error {
	switch event.EventType {
	case "expired", "del":
		return h.clearCache(event)
	case "set":
		return h.syncData(event)
	default:
		logger.Debug("No callback for event type", zap.String("event_type", event.EventType))
		return nil
	}
}

func (h *CallbackHandler) clearCache(event *models.KeyEvent) error {
	if config.AppConfig.Callback.CacheClearURL == "" {
		return nil
	}

	payload := models.CallbackRequest{
		EventType: event.EventType,
		Key:       event.Key,
		DB:        event.DB,
		Timestamp: event.Timestamp.Unix(),
	}

	return h.sendWebhook(config.AppConfig.Callback.CacheClearURL, payload)
}

func (h *CallbackHandler) syncData(event *models.KeyEvent) error {
	if config.AppConfig.Callback.DataSyncURL == "" {
		return nil
	}

	payload := models.CallbackRequest{
		EventType: event.EventType,
		Key:       event.Key,
		DB:        event.DB,
		Timestamp: event.Timestamp.Unix(),
	}

	return h.sendWebhook(config.AppConfig.Callback.DataSyncURL, payload)
}

func (h *CallbackHandler) sendWebhook(url string, payload interface{}) error {
	jsonData, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal payload: %w", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), config.AppConfig.Callback.Timeout)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-Event-Source", "redis-keyspace-notifier")

	start := time.Now()
	resp, err := h.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("webhook request failed: %w", err)
	}
	defer resp.Body.Close()

	logger.Debug("Webhook response",
		zap.String("url", url),
		zap.Int("status", resp.StatusCode),
		zap.Duration("duration", time.Since(start)))

	if resp.StatusCode >= 400 {
		return fmt.Errorf("webhook returned non-success status: %d", resp.StatusCode)
	}

	return nil
}
