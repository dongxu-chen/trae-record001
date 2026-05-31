package deadletter

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/apache/pulsar-client-go/pulsar"
	"pulsar-backlog-manager/pkg/audit"
	"pulsar-backlog-manager/pkg/monitor"
	"pulsar-backlog-manager/pkg/strategy"
)

type DeadLetterStats struct {
	Topic           string `json:"topic"`
	Subscription    string `json:"subscription"`
	TotalSentToDLQ  int64  `json:"total_sent_to_dlq"`
	TotalRetried    int64  `json:"total_retried"`
	MaxRedeliveries int    `json:"max_redeliveries"`
	DLQTopic        string `json:"dlq_topic"`
	RetryTopic      string `json:"retry_topic"`
	Enabled         bool   `json:"enabled"`
}

type topicDLQConfig struct {
	enabled         bool
	maxRedeliveries int
	dlqTopic        string
	retryTopic      string
}

type DeadLetterHandler struct {
	client   pulsar.Client
	strategy *strategy.Manager
	audit    *audit.AuditLogger
	configs  map[string]*topicDLQConfig
	stats    map[string]*DeadLetterStats
	mu       sync.Mutex
}

func NewDeadLetterHandler(pulsarClient pulsar.Client, strategyMgr *strategy.Manager, auditLog *audit.AuditLogger) *DeadLetterHandler {
	return &DeadLetterHandler{
		client:   pulsarClient,
		strategy: strategyMgr,
		audit:    auditLog,
		configs:  make(map[string]*topicDLQConfig),
		stats:    make(map[string]*DeadLetterStats),
	}
}

func (d *DeadLetterHandler) HandleBacklog(backlog monitor.TopicBacklog) {
	key := backlog.Topic + "-" + backlog.Subscription
	d.mu.Lock()
	defer d.mu.Unlock()

	if _, exists := d.configs[key]; exists {
		return
	}

	strategyCfg := d.strategy.GetStrategy(backlog.Topic)
	if strategyCfg == nil || !strategyCfg.DeadLetter.Enabled {
		return
	}

	d.applyStrategyConfig(key, backlog.Topic, backlog.Subscription, &strategyCfg.DeadLetter)
}

func (d *DeadLetterHandler) applyStrategyConfig(key, topic, subscription string, cfg *strategy.DeadLetterStrategy) {
	dlqTopic := cfg.DLQTopic
	if dlqTopic == "" {
		dlqTopic = topic + "-DLQ"
	}
	retryTopic := cfg.RetryTopic
	if retryTopic == "" {
		retryTopic = topic + "-RETRY"
	}

	d.configs[key] = &topicDLQConfig{
		enabled:         true,
		maxRedeliveries: cfg.MaxRedeliveries,
		dlqTopic:        dlqTopic,
		retryTopic:      retryTopic,
	}

	d.stats[key] = &DeadLetterStats{
		Topic:           topic,
		Subscription:    subscription,
		MaxRedeliveries: cfg.MaxRedeliveries,
		DLQTopic:        dlqTopic,
		RetryTopic:      retryTopic,
		Enabled:         true,
	}
}

func (d *DeadLetterHandler) ConfigureDLQ(topic, subscription string, maxRedeliveries int, dlqTopic, retryTopic string) {
	key := topic + "-" + subscription
	d.mu.Lock()
	defer d.mu.Unlock()

	if dlqTopic == "" {
		dlqTopic = topic + "-DLQ"
	}
	if retryTopic == "" {
		retryTopic = topic + "-RETRY"
	}

	d.configs[key] = &topicDLQConfig{
		enabled:         true,
		maxRedeliveries: maxRedeliveries,
		dlqTopic:        dlqTopic,
		retryTopic:      retryTopic,
	}

	d.stats[key] = &DeadLetterStats{
		Topic:           topic,
		Subscription:    subscription,
		MaxRedeliveries: maxRedeliveries,
		DLQTopic:        dlqTopic,
		RetryTopic:      retryTopic,
		Enabled:         true,
	}

	d.audit.Log(audit.ActionDLQConfig, topic,
		"Configured DLQ: max_redeliveries=%d, dlq_topic=%s, retry_topic=%s",
		maxRedeliveries, dlqTopic, retryTopic)
}

func (d *DeadLetterHandler) ShouldSendToDLQ(topic, subscription string, redeliveryCount int) bool {
	d.mu.Lock()
	defer d.mu.Unlock()

	key := topic + "-" + subscription
	cfg, exists := d.configs[key]
	if !exists || !cfg.enabled {
		return false
	}
	return redeliveryCount >= cfg.maxRedeliveries
}

func (d *DeadLetterHandler) SendToDLQ(topic, subscription string, messagePayload []byte, redeliveryCount int) error {
	key := topic + "-" + subscription
	d.mu.Lock()
	cfg, exists := d.configs[key]
	if !exists || !cfg.enabled {
		d.mu.Unlock()
		return fmt.Errorf("DLQ not configured for %s/%s", topic, subscription)
	}
	dlqTopic := cfg.dlqTopic
	d.mu.Unlock()

	producer, err := d.client.CreateProducer(pulsar.ProducerOptions{
		Topic: dlqTopic,
	})
	if err != nil {
		return fmt.Errorf("failed to create DLQ producer: %w", err)
	}
	defer producer.Close()

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	_, err = producer.Send(ctx, &pulsar.ProducerMessage{
		Payload: messagePayload,
		Properties: map[string]string{
			"original_topic":   topic,
			"original_sub":     subscription,
			"redelivery_count": fmt.Sprintf("%d", redeliveryCount),
			"dlq_timestamp":    time.Now().Format(time.RFC3339),
		},
	})
	if err != nil {
		return fmt.Errorf("failed to send message to DLQ: %w", err)
	}

	d.mu.Lock()
	if stat, exists := d.stats[key]; exists {
		stat.TotalSentToDLQ++
	}
	d.mu.Unlock()

	d.audit.Log(audit.ActionDLQSend, topic,
		"Sent message to DLQ %s (redelivery_count=%d)", dlqTopic, redeliveryCount)
	return nil
}

func (d *DeadLetterHandler) RetryFromDLQ(topic, subscription string, maxMessages int) (int, error) {
	key := topic + "-" + subscription
	d.mu.Lock()
	cfg, exists := d.configs[key]
	if !exists || !cfg.enabled {
		d.mu.Unlock()
		return 0, fmt.Errorf("DLQ not configured for %s/%s", topic, subscription)
	}
	dlqTopic := cfg.dlqTopic
	retryTopic := cfg.retryTopic
	d.mu.Unlock()

	reader, err := d.client.CreateReader(pulsar.ReaderOptions{
		Topic:          dlqTopic,
		StartMessageID: pulsar.EarliestMessageID(),
	})
	if err != nil {
		return 0, fmt.Errorf("failed to create DLQ reader: %w", err)
	}
	defer reader.Close()

	producer, err := d.client.CreateProducer(pulsar.ProducerOptions{
		Topic: retryTopic,
	})
	if err != nil {
		return 0, fmt.Errorf("failed to create retry producer: %w", err)
	}
	defer producer.Close()

	retried := 0
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	for retried < maxMessages {
		msg, err := reader.Next(ctx)
		if err != nil {
			break
		}

		_, err = producer.Send(ctx, &pulsar.ProducerMessage{
			Payload:    msg.Payload(),
			Properties: msg.Properties(),
		})
		if err != nil {
			break
		}
		retried++
	}

	d.mu.Lock()
	if stat, exists := d.stats[key]; exists {
		stat.TotalRetried += int64(retried)
	}
	d.mu.Unlock()

	d.audit.Log(audit.ActionDLQRetry, topic,
		"Retried %d messages from DLQ %s to %s", retried, dlqTopic, retryTopic)
	return retried, nil
}

func (d *DeadLetterHandler) GetStats(topic, subscription string) *DeadLetterStats {
	d.mu.Lock()
	defer d.mu.Unlock()
	key := topic + "-" + subscription
	if stat, exists := d.stats[key]; exists {
		result := *stat
		return &result
	}
	return nil
}

func (d *DeadLetterHandler) GetAllStats() []*DeadLetterStats {
	d.mu.Lock()
	defer d.mu.Unlock()

	result := make([]*DeadLetterStats, 0, len(d.stats))
	for _, stat := range d.stats {
		s := *stat
		result = append(result, &s)
	}
	return result
}

func (d *DeadLetterHandler) EnableDLQ(topic, subscription string) {
	d.mu.Lock()
	defer d.mu.Unlock()

	key := topic + "-" + subscription
	if cfg, exists := d.configs[key]; exists {
		cfg.enabled = true
	}
	if stat, exists := d.stats[key]; exists {
		stat.Enabled = true
	}
	d.audit.Log(audit.ActionDLQConfig, topic, "Enabled DLQ for subscription %s", subscription)
}

func (d *DeadLetterHandler) DisableDLQ(topic, subscription string) {
	d.mu.Lock()
	defer d.mu.Unlock()

	key := topic + "-" + subscription
	if cfg, exists := d.configs[key]; exists {
		cfg.enabled = false
	}
	if stat, exists := d.stats[key]; exists {
		stat.Enabled = false
	}
	d.audit.Log(audit.ActionDLQConfig, topic, "Disabled DLQ for subscription %s", subscription)
}
