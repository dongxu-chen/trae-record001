package alert

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"monitor-agent/internal/config"
)

type AlertManager struct {
	mu               sync.RWMutex
	cpuHighCount     int
	cpuAlerted       bool
	memoryHighCount  int
	memoryAlerted    bool
}

func NewAlertManager() *AlertManager {
	return &AlertManager{}
}

type DingTalkMessage struct {
	MsgType string                 `json:"msgtype"`
	Text    DingTalkText           `json:"text"`
	At      DingTalkAt             `json:"at"`
}

type DingTalkText struct {
	Content string `json:"content"`
}

type DingTalkAt struct {
	AtMobiles []string `json:"atMobiles"`
	IsAtAll   bool     `json:"isAtAll"`
}

func (a *AlertManager) CheckAndAlert(cpuUsage, memoryUsage float64) {
	cfg := config.GetConfig()
	if !cfg.Alert.Enabled {
		return
	}

	now := time.Now()
	if cfg.Alert.IsSilentPeriod(now) {
		log.Println("In silent period, skipping alert check")
		return
	}

	thresholdCount := a.calculateThresholdCount(cfg.Alert.GetDuration(), cfg.Collector.GetInterval())

	a.checkCPU(cpuUsage, cfg.Alert.CPUThreshold, thresholdCount)
	a.checkMemory(memoryUsage, cfg.Alert.MemoryThreshold, thresholdCount)
}

func (a *AlertManager) calculateThresholdCount(duration, interval time.Duration) int {
	if interval <= 0 {
		interval = 10 * time.Second
	}
	count := int(duration / interval)
	if count < 1 {
		count = 1
	}
	return count
}

func (a *AlertManager) checkCPU(cpuUsage, threshold float64, thresholdCount int) {
	a.mu.Lock()
	defer a.mu.Unlock()

	if cpuUsage >= threshold {
		a.cpuHighCount++
		log.Printf("CPU usage %.2f%% exceeded threshold %.2f%%, consecutive count: %d/%d", 
			cpuUsage, threshold, a.cpuHighCount, thresholdCount)
		
		if a.cpuHighCount >= thresholdCount && !a.cpuAlerted {
			a.sendCPUAlert(cpuUsage, threshold, a.cpuHighCount)
			a.cpuAlerted = true
		}
	} else {
		if a.cpuHighCount > 0 {
			log.Printf("CPU usage %.2f%% back to normal, resetting consecutive count (was: %d)", 
				cpuUsage, a.cpuHighCount)
		}
		a.cpuHighCount = 0
		a.cpuAlerted = false
	}
}

func (a *AlertManager) checkMemory(memoryUsage, threshold float64, thresholdCount int) {
	a.mu.Lock()
	defer a.mu.Unlock()

	if memoryUsage >= threshold {
		a.memoryHighCount++
		log.Printf("Memory usage %.2f%% exceeded threshold %.2f%%, consecutive count: %d/%d", 
			memoryUsage, threshold, a.memoryHighCount, thresholdCount)
		
		if a.memoryHighCount >= thresholdCount && !a.memoryAlerted {
			a.sendMemoryAlert(memoryUsage, threshold, a.memoryHighCount)
			a.memoryAlerted = true
		}
	} else {
		if a.memoryHighCount > 0 {
			log.Printf("Memory usage %.2f%% back to normal, resetting consecutive count (was: %d)", 
				memoryUsage, a.memoryHighCount)
		}
		a.memoryHighCount = 0
		a.memoryAlerted = false
	}
}

func (a *AlertManager) sendCPUAlert(cpuUsage, threshold float64, consecutiveCount int) {
	cfg := config.GetConfig()
	hostname, _ := osHostname()
	duration := time.Duration(consecutiveCount) * cfg.Collector.GetInterval()
	content := fmt.Sprintf(
		"【服务器告警】CPU使用率过高\n\n主机: %s\n当前CPU使用率: %.2f%%\n阈值: %.2f%%\n连续超过: %d次 (约%v)\n告警时间: %s",
		hostname, cpuUsage, threshold, consecutiveCount, duration, time.Now().Format("2006-01-02 15:04:05"),
	)
	a.sendDingTalk(content, cfg.DingTalk)
}

func (a *AlertManager) sendMemoryAlert(memoryUsage, threshold float64, consecutiveCount int) {
	cfg := config.GetConfig()
	hostname, _ := osHostname()
	duration := time.Duration(consecutiveCount) * cfg.Collector.GetInterval()
	content := fmt.Sprintf(
		"【服务器告警】内存使用率过高\n\n主机: %s\n当前内存使用率: %.2f%%\n阈值: %.2f%%\n连续超过: %d次 (约%v)\n告警时间: %s",
		hostname, memoryUsage, threshold, consecutiveCount, duration, time.Now().Format("2006-01-02 15:04:05"),
	)
	a.sendDingTalk(content, cfg.DingTalk)
}

func (a *AlertManager) sendDingTalk(content string, dtCfg config.DingTalkConfig) {
	if dtCfg.WebhookURL == "" {
		log.Println("DingTalk webhook URL not configured, skipping alert")
		return
	}

	msg := DingTalkMessage{
		MsgType: "text",
		Text: DingTalkText{
			Content: content,
		},
		At: DingTalkAt{
			AtMobiles: dtCfg.AtMobiles,
			IsAtAll:   dtCfg.IsAtAll,
		},
	}

	jsonData, err := json.Marshal(msg)
	if err != nil {
		log.Printf("Failed to marshal DingTalk message: %v", err)
		return
	}

	url := dtCfg.WebhookURL
	if dtCfg.Secret != "" {
		timestamp := time.Now().UnixMilli()
		sign := generateDingTalkSign(timestamp, dtCfg.Secret)
		url = fmt.Sprintf("%s&timestamp=%d&sign=%s", url, timestamp, sign)
	}

	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		log.Printf("Failed to send DingTalk alert: %v", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		log.Printf("DingTalk alert returned status: %d", resp.StatusCode)
		return
	}

	log.Println("DingTalk alert sent successfully")
}

func generateDingTalkSign(timestamp int64, secret string) string {
	stringToSign := fmt.Sprintf("%d\n%s", timestamp, secret)
	h := hmac.New(sha256.New, []byte(secret))
	h.Write([]byte(stringToSign))
	signData := h.Sum(nil)
	return base64.StdEncoding.EncodeToString(signData)
}

func osHostname() (string, error) {
	return os.Hostname()
}
