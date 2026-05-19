package notifications

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"time"

	"go.uber.org/zap"
)

// AlertRouter handles routing alerts to multiple channels
type AlertRouter struct {
	DingTalkConfig *DingTalkConfig
	WeWorkConfig   *WeWorkConfig
	Logger         *zap.Logger
}

// DingTalkConfig holds DingTalk webhook configuration
type DingTalkConfig struct {
	WebhookURL string
	Secret     string
	AtMobiles  []string
	AtAll      bool
}

// WeWorkConfig holds WeCom webhook configuration
type WeWorkConfig struct {
	WebhookURL string
}

// AlertMessage represents an alert to send
type AlertMessage struct {
	Title       string
	Description string
	Severity    string // High, Medium, Low
	Timestamp   time.Time
	Labels      map[string]string
}

// SendAlert sends an alert to all configured channels
func (ar *AlertRouter) SendAlert(alert AlertMessage) error {
	var errs []error

	if ar.DingTalkConfig != nil && ar.DingTalkConfig.WebhookURL != "" {
		if err := ar.sendToDingTalk(alert); err != nil {
			errs = append(errs, fmt.Errorf("dingtalk: %w", err))
		}
	}

	if ar.WeWorkConfig != nil && ar.WeWorkConfig.WebhookURL != "" {
		if err := ar.sendToWeWork(alert); err != nil {
			errs = append(errs, fmt.Errorf("wework: %w", err))
		}
	}

	if len(errs) > 0 {
		return fmt.Errorf("failed to send alerts: %v", errs)
	}
	return nil
}

func (ar *AlertRouter) sendToDingTalk(alert AlertMessage) error {
	dt := ar.DingTalkConfig

	// Build markdown content
	markdown := fmt.Sprintf("## %s\n\n", alert.Title)
	markdown += fmt.Sprintf("**Severity:** %s\n\n", alert.Severity)
	markdown += fmt.Sprintf("**Time:** %s\n\n", alert.Timestamp.Format(time.RFC3339))
	markdown += fmt.Sprintf("**Description:**\n%s\n\n", alert.Description)

	if len(alert.Labels) > 0 {
		markdown += "**Labels:**\n"
		for k, v := range alert.Labels {
			markdown += fmt.Sprintf("- %s: %s\n", k, v)
		}
	}

	payload := map[string]interface{}{
		"msgtype": "markdown",
		"markdown": map[string]string{
			"title": alert.Title,
			"text":  markdown,
		},
	}

	// Add @ mentions
	if dt.AtAll {
		payload["at"] = map[string]interface{}{"isAtAll": true}
	} else if len(dt.AtMobiles) > 0 {
		payload["at"] = map[string]interface{}{"atMobiles": dt.AtMobiles}
	}

	url := dt.WebhookURL

	// Add signature if secret provided
	if dt.Secret != "" {
		timestamp := strconv.FormatInt(time.Now().UnixMilli(), 10)
		stringToSign := timestamp + "\n" + dt.Secret
		h := hmac.New(sha256.New, []byte(dt.Secret))
		h.Write([]byte(stringToSign))
		signature := base64.StdEncoding.EncodeToString(h.Sum(nil))
		url += fmt.Sprintf("&timestamp=%s&sign=%s", timestamp, signature)
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	resp, err := http.Post(url, "application/json", bytes.NewReader(body))
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("unexpected status: %d, body: %s", resp.StatusCode, string(respBody))
	}

	ar.Logger.Info("Alert sent to DingTalk", zap.String("title", alert.Title))
	return nil
}

func (ar *AlertRouter) sendToWeWork(alert AlertMessage) error {
	ww := ar.WeWorkConfig

	// Build markdown content
	markdown := fmt.Sprintf("## %s\n", alert.Title)
	markdown += fmt.Sprintf("> **Severity:** <font color=\"%s\">%s</font>\n",
		getSeverityColor(alert.Severity), alert.Severity)
	markdown += fmt.Sprintf("> **Time:** %s\n", alert.Timestamp.Format(time.RFC3339))
	markdown += fmt.Sprintf("> **Description:**\n%s\n", alert.Description)

	if len(alert.Labels) > 0 {
		markdown += "> **Labels:**\n"
		for k, v := range alert.Labels {
			markdown += fmt.Sprintf("> - %s: %s\n", k, v)
		}
	}

	payload := map[string]interface{}{
		"msgtype": "markdown",
		"markdown": map[string]string{
			"content": markdown,
		},
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return err
	}

	resp, err := http.Post(ww.WebhookURL, "application/json", bytes.NewReader(body))
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("unexpected status: %d, body: %s", resp.StatusCode, string(respBody))
	}

	ar.Logger.Info("Alert sent to WeWork", zap.String("title", alert.Title))
	return nil
}

func getSeverityColor(severity string) string {
	switch severity {
	case "High":
		return "red"
	case "Medium":
		return "orange"
	default:
		return "green"
	}
}
